# import asyncio
# from typing import Optional, Dict, Any, List, Union
# from contextlib import AsyncExitStack
# import logging
# import os
# import sys
# import json
# import time
# import re
# from difflib import get_close_matches

# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client

# from anthropic import Anthropic
# from anthropic.types import ContentBlock, ToolUseBlock, TextBlock
# from dotenv import load_dotenv

# # Import LangChain components
# from langchain.memory import ConversationBufferMemory
# from langchain_core.prompts import PromptTemplate
# from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
# from langchain_anthropic import ChatAnthropic  # Remove AnthropicLLMWrapper
# from langchain_core.tools import Tool
# from langchain_core.pydantic_v1 import BaseModel, Field, validator

# # Load environment variables from .env
# load_dotenv()

# # Set up logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.StreamHandler(sys.stdout)
#     ]
# )
# logger = logging.getLogger('solarwinds_client')

# class SolarWindsClient:
#     def __init__(self):
#         # Initialize session and client objects
#         self.session: Optional[ClientSession] = None
#         self.exit_stack = AsyncExitStack()
        
#         api_key = os.getenv("ANTHROPIC_API_KEY")
#         if not api_key:
#             sys.exit(1)
            
#         # Initialize Anthropic API client
#         self.anthropic = Anthropic(api_key=api_key)
        
#         # Initialize LangChain components
#         self.llm = ChatAnthropic(
#             model="claude-3-5-haiku-20241022", 
#             anthropic_api_key=api_key, 
#             temperature=0.3
#         )
        
#         # Set up conversation memory
#         self.memory = ConversationBufferMemory(
#             return_messages=True,
#             memory_key="chat_history",
#             input_key="input",
#             output_key="output"
#         )
        
#         # Dictionary for fuzzy matching corrections
#         self.common_terms = {
#             "priorities": ["Low", "Medium", "High", "Critical"],
#             "states": ["New", "Open", "In Progress", "Pending", "Resolved", "Closed"],
#             "common_fields": ["description", "name", "priority", "state", "requester", "assignee", "department", "site"]
#         }
        
#         # Additional mappings for conversational terms to formal parameters
#         self.intent_mappings = {
#             "states": {
#                 "assigned": "In Progress",
#                 "in-progress": "In Progress", 
#                 "inprogress": "In Progress",
#                 "in_progress": "In Progress",
#                 "open": "Open",
#                 "new": "New",
#                 "pending": "Pending",
#                 "resolved": "Resolved",
#                 "closed": "Closed",
#                 "done": "Closed",
#                 "completed": "Closed",
#                 "finished": "Closed"
#             },
#             "priorities": {
#                 "urgent": "Critical",
#                 "important": "High",
#                 "normal": "Medium",
#                 "low priority": "Low",
#                 "high priority": "High",
#                 "medium priority": "Medium",
#                 "critical priority": "Critical"
#             },
#             "entities": {
#                 "ticket": "incident",
#                 "tickets": "incidents",
#                 "task": "incident",
#                 "tasks": "incidents",
#                 "issue": "incident",
#                 "issues": "incidents",
#                 "problem": "problem",
#                 "problems": "problems"
#             }
#         }
        
#         # To store tools for LangChain
#         self.tools = []
#         self.tool_map = {}
        
#         logger.info("Initialized SolarWindsClient with LangChain and Anthropic API")
        
#     async def connect_to_server(self, server_script_path: str):
#         """Connect to the SolarWinds Service Desk MCP server"""
        
#         # Check if file exists
#         if not os.path.exists(server_script_path):
#             logger.error(f"Server script not found at path: {server_script_path}")
#             print(f"\n⚠️ ERROR: Server script not found at: {server_script_path}")
#             sys.exit(1)
            
#         is_python = server_script_path.endswith('.py')
#         is_js = server_script_path.endswith('.js')
#         if not (is_python or is_js):
#             raise ValueError("Server script must be a .py or .js file")
            
#         command = "python" if is_python else "node"
        
#         server_params = StdioServerParameters(
#             command=command,
#             args=[server_script_path],
#             env=None
#         )
        
#         print("\n🔄 Connecting to server...\n")
        
#         try:
#             stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
#             self.stdio, self.write = stdio_transport
            
#             self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            
#             try:
#                 await asyncio.wait_for(self.session.initialize(), timeout=60.0)
#             except asyncio.TimeoutError:
#                 print("⚠️ Initialization timed out but we'll continue anyway")
                
#             # Get available tools for LangChain integration
#             await self._setup_tools()
            
#         except asyncio.TimeoutError:
#             logger.error("Timeout connecting to server")
#             print("\n⚠️ ERROR: Connection to server timed out. Make sure the server is running.")
#             sys.exit(1)
#         except Exception as e:
#             logger.error(f"Error connecting to server: {e}", exc_info=True)
#             print(f"\n⚠️ ERROR: Failed to connect to server: {str(e)}")
#             sys.exit(1)
            
#     async def _setup_tools(self):
#         """Set up LangChain tools from MCP tools"""
#         if not self.session:
#             logger.error("Session not initialized")
#             return
            
#         # Get the available tools from MCP server
#         response = await self.session.list_tools()
#         mcp_tools = response.tools
        
#         # Add tool names to common terms for fuzzy matching
#         self.common_terms["tool_names"] = [tool.name for tool in mcp_tools]
        
#         # Extract parameter names from tools for fuzzy matching
#         param_names = set()
#         for tool in mcp_tools:
#             if tool.inputSchema and "properties" in tool.inputSchema:
#                 for param in tool.inputSchema["properties"]:
#                     param_names.add(param)
#         self.common_terms["parameter_names"] = list(param_names)
        
#         # Create LangChain tools from MCP tools
#         for mcp_tool in mcp_tools:
#             tool_name = mcp_tool.name
#             tool_description = mcp_tool.description
#             tool_schema = mcp_tool.inputSchema
            
#             # Create a Tool wrapper for this MCP tool
#             tool = Tool(
#                 name=tool_name,
#                 description=tool_description,
#                 func=lambda tool_name=tool_name, **kwargs: self._execute_tool(tool_name, kwargs),  # Add comma here
#                 args_schema=None  # We'll handle schema validation ourselves
#             )
            
#             # Store reference to tool and schema
#             self.tools.append(tool)
#             self.tool_map[tool_name] = tool_schema
            
#         logger.info(f"Loaded {len(self.tools)} tools from MCP server")
    
#     async def _execute_tool(self, tool_name: str, args: Dict[str, Any]):
#         """Execute an MCP tool with given arguments"""
#         logger.info(f"Executing tool {tool_name} with args: {args}")
        
#         # Display tool call (for "flashing" effect)
#         tool_call_display = f"\n[🔧 Calling tool: {tool_name}]\n"
#         tool_call_display += f"Parameters: {json.dumps(args, indent=2)}\n"
#         print(tool_call_display)
        
#         try:
#             # Execute the tool using MCP session
#             start_time = time.time()
#             result = await self.session.call_tool(tool_name, args)
#             execution_time = time.time() - start_time
            
#             # Format and display result
#             result_str = "".join(item.text for item in result.content if hasattr(item, 'text'))
            
#             tool_result_display = "[📊 Tool result]:\n"
#             if len(result_str) > 500:
#                 tool_result_display += f"{result_str[:500]}...\n[Result truncated, full data sent to Claude]\n"
#             else:
#                 tool_result_display += f"{result_str}\n"
            
#             print(tool_result_display)
            
#             # Return the result as a string
#             return result_str
            
#         except Exception as e:
#             error_message = f"❌ Error executing tool {tool_name}: {str(e)}"
#             print(error_message)
#             return error_message
    
#     def _clean_and_correct_query(self, query: str) -> str:
#         """
#         Apply fuzzy matching, error correction, and intent mapping to the user query.
#         This helps handle minor spelling errors, typos, and conversational language.
#         """
#         cleaned_query = query.strip()
        
#         # Store corrections for display
#         corrections = []
        
#         # Function to find and replace misspelled terms
#         def replace_misspelled(text, term_list, threshold=0.75):
#             words = re.findall(r'\b\w+\b', text)
#             for word in words:
#                 if word.lower() not in [t.lower() for t in term_list]:
#                     matches = get_close_matches(word.lower(), [t.lower() for t in term_list], n=1, cutoff=threshold)
#                     if matches:
#                         best_match_index = [t.lower() for t in term_list].index(matches[0])
#                         correct_term = term_list[best_match_index]
#                         if word != correct_term:
#                             old_text = text
#                             # Replace with correct casing
#                             pattern = re.compile(re.escape(word), re.IGNORECASE)
#                             text = pattern.sub(correct_term, text, 1)
#                             if old_text != text:
#                                 corrections.append(f"'{word}' → '{correct_term}'")
#             return text
        
#         # Handle intent mapping for states
#         for state_term, formal_state in self.intent_mappings["states"].items():
#             # Look for patterns like "state=assigned", "state is assigned", "state assigned"
#             patterns = [
#                 f"state\\s*=\\s*{state_term}",
#                 f"state\\s+is\\s+{state_term}",
#                 f"state\\s+{state_term}",
#                 f"status\\s*=\\s*{state_term}",
#                 f"status\\s+is\\s+{state_term}",
#                 f"status\\s+{state_term}"
#             ]
            
#             for pattern in patterns:
#                 if re.search(pattern, cleaned_query, re.IGNORECASE):
#                     old_query = cleaned_query
#                     cleaned_query = re.sub(pattern, f"state=\"{formal_state}\"", cleaned_query, flags=re.IGNORECASE)
#                     if old_query != cleaned_query:
#                         corrections.append(f"'{state_term}' → '{formal_state}' (state)")
        
#         # Handle intent mapping for priorities
#         for priority_term, formal_priority in self.intent_mappings["priorities"].items():
#             # Look for patterns like "priority=high", "priority is high", "high priority"
#             patterns = [
#                 f"priority\\s*=\\s*{priority_term}",
#                 f"priority\\s+is\\s+{priority_term}",
#                 f"priority\\s+{priority_term}",
#                 f"{priority_term}\\s+priority"
#             ]
            
#             for pattern in patterns:
#                 if re.search(pattern, cleaned_query, re.IGNORECASE):
#                     old_query = cleaned_query
#                     cleaned_query = re.sub(pattern, f"priority=\"{formal_priority}\"", cleaned_query, flags=re.IGNORECASE)
#                     if old_query != cleaned_query:
#                         corrections.append(f"'{priority_term}' → '{formal_priority}' (priority)")
        
#         # Handle entity mappings
#         for entity_term, formal_entity in self.intent_mappings["entities"].items():
#             if re.search(r'\b' + re.escape(entity_term) + r'\b', cleaned_query, re.IGNORECASE):
#                 old_query = cleaned_query
#                 cleaned_query = re.sub(r'\b' + re.escape(entity_term) + r'\b', formal_entity, cleaned_query, flags=re.IGNORECASE)
#                 if old_query != cleaned_query:
#                     corrections.append(f"'{entity_term}' → '{formal_entity}'")
        
#         # Correct common misspellings in query
#         for category, terms in self.common_terms.items():
#             cleaned_query = replace_misspelled(cleaned_query, terms)
        
#         # Correct email addresses with common typos
#         email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
#         emails = re.findall(email_pattern, cleaned_query)
#         for email in emails:
#             if '@' in email:
#                 # Check common email domain typos
#                 domain = email.split('@')[1]
#                 common_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]
#                 for correct_domain in common_domains:
#                     if domain.lower() != correct_domain and get_close_matches(domain.lower(), [correct_domain], n=1, cutoff=0.75):
#                         corrected_email = email.replace(domain, correct_domain)
#                         cleaned_query = cleaned_query.replace(email, corrected_email)
#                         corrections.append(f"'{email}' → '{corrected_email}'")
#                         break
        
#         # Special handling for specific queries
#         if "assigned" in cleaned_query.lower() and "state" not in cleaned_query.lower():
#             # If someone asks about "assigned incidents" without specifying state
#             if any(term in cleaned_query.lower() for term in ["incident", "incidents", "ticket", "tickets"]):
#                 old_query = cleaned_query
#                 cleaned_query = cleaned_query + " with state=\"In Progress\""
#                 corrections.append(f"Added 'with state=\"In Progress\"' to query about assigned incidents")
        
#         # Display corrections to the user if any were made
#         if corrections:
#             print("\n🔍 Applied corrections and interpretations:")
#             for correction in corrections:
#                 print(f"  - {correction}")
        
#         return cleaned_query

#     async def process_query_with_langchain(self, query: str) -> str:
#         """Process a query using LangChain, Anthropic Claude, and available SolarWinds tools"""
#         if not self.session:
#             logger.error("Session not initialized")
#             return "Error: Not connected to server."
        
#         # Clean and correct the query
#         cleaned_query = self._clean_and_correct_query(query)
        
#         # Prepare the input for LangChain
#         print("\n🔄 Thinking...")
        
#         try:
#             # Add the query to memory
#             langchain_input = {
#                 "input": cleaned_query,
#                 "chat_history": self.memory.load_memory_variables({})["chat_history"]
#             }
            
#             # Define system message to help guide Claude with more context understanding
#             system_message = SystemMessage(
#                 content=(
#                     "You are an AI assistant for SolarWinds Service Desk that understands user intent and context deeply. "
#                     "You have access to various tools for interacting with the Service Desk API. "
#                     "Your goal is to understand the user's actual intent, not just literal requests. "
#                     "For example, if a user asks about 'assigned incidents', they likely mean incidents with state='In Progress' or they want incidents with a specific assignee. "
#                     "Be flexible and intelligent in interpreting user requests - map informal terms to formal parameters. "
#                     "Common mappings include:"
#                     "- 'assigned' → state='In Progress' or looking for incidents with any assignee"
#                     "- 'resolved' → state='Resolved' or state='Closed'"
#                     "- 'open' → state='Open' or state='New'"
#                     "- 'ticket' → incident"
#                     "- 'user' → either requester or assignee depending on context"
#                     "\n\n"
#                     "When in doubt about what the user wants:"
#                     "1. Infer their most likely intent based on conversation history and common workflows"
#                     "2. Choose the most relevant tool based on that intent"
#                     "3. If multiple interpretations are possible, pick the most likely one and explain your reasoning"
#                     "\n\n"
#                     "Be concise and accurate in your responses while understanding that users speak conversationally, not with precise API parameters."
#                 )
#             )
            
#             # Create a human message for the current query
#             human_message = HumanMessage(content=cleaned_query)
            
#             # Prepare tool specifications for Claude
#             claude_tools = []
#             for tool in self.tools:
#                 tool_schema = self.tool_map.get(tool.name, {})
#                 claude_tools.append({
#                     "name": tool.name,
#                     "description": tool.description,
#                     "input_schema": tool_schema
#                 })
            
#             # Get history from memory
#             history = self.memory.load_memory_variables({}).get("chat_history", [])
            
#             # Convert history to appropriate format for Claude API with improved context handling
#             claude_messages = []
            
#             # We'll use the system message as a top-level parameter, not in the messages array
#             system_prompt = system_message.content
            
#             # Add conversation history
#             tool_use_ids = set()  # Track tool use IDs to ensure proper pairing
#             last_assistant_message = None
            
#             for i, msg in enumerate(history):
#                 if isinstance(msg, HumanMessage):
#                     claude_messages.append({"role": "user", "content": msg.content})
#                 elif isinstance(msg, AIMessage):
#                     # Store current message and check if it contains tool_use
#                     assistant_content = msg.content
#                     last_assistant_message = {"role": "assistant", "content": assistant_content}
#                     claude_messages.append(last_assistant_message)
                    
#                     # Extract tool_use_ids from this message for validation
#                     if isinstance(assistant_content, list):
#                         for item in assistant_content:
#                             if isinstance(item, dict) and item.get("type") == "tool_use":
#                                 tool_use_ids.add(item.get("id"))
#                 elif isinstance(msg, ToolMessage):
#                     # Handle tool messages properly with proper pairing
#                     if hasattr(msg, 'tool_use_id') and msg.tool_use_id:
#                         claude_messages.append({
#                             "role": "user", 
#                             "content": [{"type": "tool_result", "tool_use_id": msg.tool_use_id, "content": [{"type": "text", "text": msg.content}]}]
#                         })
#                         # Mark this tool_use_id as handled
#                         if msg.tool_use_id in tool_use_ids:
#                             tool_use_ids.remove(msg.tool_use_id)
#                     else:
#                         # Fallback for tool messages without tool_use_id
#                         claude_messages.append({"role": "user", "content": f"Tool result: {msg.content}"})
            
#             # Ensure no dangling tool uses (uncomment if needed for debugging)
#             # if tool_use_ids:
#             #     logger.warning(f"Found {len(tool_use_ids)} unmatched tool_use messages in history")
            
#             # Add the current query with context enhancement
#             # Look for patterns that might indicate specific intent and add context
#             enhanced_query = f"{cleaned_query}\n\n(Context: This is a follow-up to the previous conversation, remember to maintain context)"
            
#             # Add the enhanced query
#             claude_messages.append({"role": "user", "content": enhanced_query})
            
#             # Create the first Claude API call
#             response = self.anthropic.messages.create(
#                 model="claude-3-5-haiku-20241022",
#                 max_tokens=1500,
#                 system=system_prompt,  # System as top-level parameter
#                 messages=claude_messages,
#                 tools=claude_tools,
#                 temperature=0.3
#             )
            
#             # Parse and process the response
#             final_text = []
#             assistant_response = []
            
#             for content in response.content:
#                 if content.type == 'text':
#                     final_text.append(content.text)
#                     assistant_response.append(content)
#                 elif content.type == 'tool_use':
#                     tool_name = content.name
#                     tool_args = content.input
#                     tool_id = content.id
                    
#                     try:
#                         # Use the _execute_tool method to run the tool
#                         result = await self._execute_tool(tool_name, tool_args)
                        
#                         # If we had successful tool execution, update the Claude messages sequence
#                         claude_messages.append({"role": "assistant", "content": [content]})
#                         claude_messages.append({
#                             "role": "user", 
#                             "content": [
#                                 {
#                                     "type": "tool_result", 
#                                     "tool_use_id": tool_id, 
#                                     "content": [{"type": "text", "text": result}]
#                                 }
#                             ]
#                         })
                        
#                         # Get the next response from Claude
#                         print("🔄 Processing results...")
#                         follow_up_response = self.anthropic.messages.create(
#                             model="claude-3-5-haiku-20241022",
#                             max_tokens=1500,
#                             system=system_prompt,  # System as top-level parameter
#                             messages=claude_messages,
#                             tools=claude_tools,
#                             temperature=0.3
#                         )
                        
#                         # Add the follow-up response to final text
#                         for content_item in follow_up_response.content:
#                             if content_item.type == 'text':
#                                 final_text.append(content_item.text)
#                                 assistant_response.append(content_item)
                        
#                     except Exception as e:
#                         logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
#                         error_message = f"❌ Error executing tool {tool_name}: {str(e)}"
#                         final_text.append(error_message)
                        
#                         # Add the error message to the Claude messages sequence
#                         claude_messages.append({"role": "assistant", "content": [content]})
#                         claude_messages.append({
#                             "role": "user", 
#                             "content": [
#                                 {
#                                     "type": "tool_result", 
#                                     "tool_use_id": tool_id, 
#                                     "content": [{"type": "text", "text": error_message}]
#                                 }
#                             ]
#                         })
            
#             # Update memory with the latest exchange
#             output_text = "\n".join(final_text)
#             self.memory.save_context({"input": cleaned_query}, {"output": output_text})
            
#             # Return the final response text
#             return output_text
            
#         except Exception as e:
#             logger.error(f"Error processing query with LangChain: {e}", exc_info=True)
#             return f"Error processing your request: {str(e)}"

#     async def chat_loop(self):
#         """Run an interactive chat loop for SolarWinds Service Desk"""
#         print("\n✨ SolarWinds Service Desk Client Started! ✨")
#         print("You can ask questions about tickets, users, departments, etc.")
#         print("Type 'quit' to exit.")
        
#         # Display some example queries
#         print("\nExample queries you can try:")
#         print("- Show me open incidents")
#         print("- Create a new incident for network outage")
#         print("- Search for users in the IT department")
#         print("- What are the active alerts in the system?")
#         print("- Analyze incidents for last month")
        
#         while True:
#             try:
#                 query = input("\n💬 Query: ").strip()
                
#                 if not query:
#                     continue
                    
#                 if query.lower() in ['quit', 'exit']:
#                     logger.info("User requested exit")
#                     print("\n👋 Goodbye!")
#                     break
                
#                 print("\n🔄 Processing your request...")
#                 # Use the LangChain-based processing
#                 response = await self.process_query_with_langchain(query)
#                 print("\n📝 Response:")
#                 print(response)
                    
#             except KeyboardInterrupt:
#                 logger.info("KeyboardInterrupt detected")
#                 print("\n👋 Exiting...")
#                 break
#             except Exception as e:
#                 logger.error(f"Error in chat loop: {e}", exc_info=True)
#                 print(f"\n❌ Error: {str(e)}")
    
#     async def cleanup(self):
#         """Clean up resources"""
#         logger.info("Cleaning up resources")
#         await self.exit_stack.aclose()
#         logger.info("Cleanup complete")

# async def main():
#     print("\n🌟 SolarWinds MCP Client 🌟")
    
#     if len(asyncio.get_event_loop()._ready) > 0:
#         # Reset the event loop if it's been used
#         asyncio.set_event_loop(asyncio.new_event_loop())
        
#     import sys
#     if len(sys.argv) < 2:
#         print("Usage: python client.py <path_to_server_script>")
#         print("\nExample:")
#         print("  python client.py server.py")
#         print("  python client.py /full/path/to/server.py")
#         sys.exit(1)
        
#     server_path = sys.argv[1]
    
#     # Get the absolute path
#     server_path = os.path.abspath(server_path)
#     logger.info(f"Using server path: {server_path}")
        
#     client = SolarWindsClient()
#     try:
#         await client.connect_to_server(server_path)
#         await client.chat_loop()
#     except Exception as e:
#         logger.error(f"Unexpected error: {e}", exc_info=True)
#         print(f"\n❌ Fatal error: {str(e)}")
#     finally:
#         await client.cleanup()

# if __name__ == "__main__":
#     asyncio.run(main())

import asyncio
from typing import Optional, Dict, Any, List, Union
from contextlib import AsyncExitStack
import logging
import os
import sys
import json
import time
import re
from difflib import get_close_matches
from datetime import datetime, timezone
from typing import Tuple, Optional, Dict, Any, List, Union

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field, validator
from anthropic import Anthropic
from anthropic.types import ContentBlock, ToolUseBlock, TextBlock
from dotenv import load_dotenv

# Import LangChain components
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import Tool
from langchain_core.pydantic_v1 import BaseModel, Field, validator

# Load environment variables from .env
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('solarwinds_client')

class SolarWindsClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            sys.exit(1)
            
        # Initialize Anthropic API client
        self.anthropic = Anthropic(api_key=api_key)
        
        # Initialize LangChain components
        self.llm = ChatAnthropic(
            model="claude-3-5-haiku-20241022", 
            anthropic_api_key=api_key, 
            temperature=0.3
        )
        
        # Improve conversation memory to maintain longer context
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history",
            input_key="input",
            output_key="output",
            max_token_limit=100000  # Increase token limit for more context
        )
        
        # Chat session context for maintaining state across interactions
        self.chat_context = {
            "current_incident": None,
            "current_problem": None,
            "current_task": None,
            "session_start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_info": {}
        }
        
        # Dictionary for fuzzy matching corrections
        self.common_terms = {
            "priorities": ["Low", "Medium", "High", "Critical"],
            "states": ["New", "Open", "In Progress", "Pending", "Resolved", "Closed"],
            "common_fields": ["description", "name", "priority", "state", "requester", "assignee", "department", "site"]
        }
        
        # Additional mappings for conversational terms to formal parameters
        self.intent_mappings = {
            "states": {
                "assigned": "In Progress",
                "in-progress": "In Progress", 
                "inprogress": "In Progress",
                "in_progress": "In Progress",
                "open": "Open",
                "new": "New",
                "pending": "Pending",
                "resolved": "Resolved",
                "closed": "Closed",
                "done": "Closed",
                "completed": "Closed",
                "finished": "Closed"
            },
            "priorities": {
                "urgent": "Critical",
                "important": "High",
                "normal": "Medium",
                "low priority": "Low",
                "high priority": "High",
                "medium priority": "Medium",
                "critical priority": "Critical"
            },
            "entities": {
                "ticket": "incident",
                "tickets": "incidents",
                "task": "incident",
                "tasks": "incidents",
                "issue": "incident",
                "issues": "incidents",
                "problem": "problem",
                "problems": "problems"
            }
        }
        
        # To store tools for LangChain
        self.tools = []
        self.tool_map = {}
        
        logger.info("Initialized SolarWindsClient with LangChain and Anthropic API")
        
    async def connect_to_server(self, server_script_path: str):
        """Connect to the SolarWinds Service Desk MCP server"""
        
        # Check if file exists
        if not os.path.exists(server_script_path):
            logger.error(f"Server script not found at path: {server_script_path}")
            print(f"\n⚠️ ERROR: Server script not found at: {server_script_path}")
            sys.exit(1)
            
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        print("\n🔄 Connecting to server...\n")
        
        try:
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            
            try:
                await asyncio.wait_for(self.session.initialize(), timeout=60.0)
            except asyncio.TimeoutError:
                print("⚠️ Initialization timed out but we'll continue anyway")
                
            # Get available tools for LangChain integration
            await self._setup_tools()
            
        except asyncio.TimeoutError:
            logger.error("Timeout connecting to server")
            print("\n⚠️ ERROR: Connection to server timed out. Make sure the server is running.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error connecting to server: {e}", exc_info=True)
            print(f"\n⚠️ ERROR: Failed to connect to server: {str(e)}")
            sys.exit(1)
            
    async def _setup_tools(self):
        """Set up LangChain tools from MCP tools"""
        if not self.session:
            logger.error("Session not initialized")
            return
            
        # Get the available tools from MCP server
        response = await self.session.list_tools()
        mcp_tools = response.tools
        
        # Add tool names to common terms for fuzzy matching
        self.common_terms["tool_names"] = [tool.name for tool in mcp_tools]
        
        # Extract parameter names from tools for fuzzy matching
        param_names = set()
        for tool in mcp_tools:
            if tool.inputSchema and "properties" in tool.inputSchema:
                for param in tool.inputSchema["properties"]:
                    param_names.add(param)
        self.common_terms["parameter_names"] = list(param_names)
        
        # Create LangChain tools from MCP tools
        for mcp_tool in mcp_tools:
            tool_name = mcp_tool.name
            tool_description = mcp_tool.description
            tool_schema = mcp_tool.inputSchema
            
            # Create a Tool wrapper for this MCP tool
            tool = Tool(
                name=tool_name,
                description=tool_description,
                func=lambda tool_name=tool_name, **kwargs: self._execute_tool(tool_name, kwargs),
                args_schema=None  # We'll handle schema validation ourselves
            )
            
            # Store reference to tool and schema
            self.tools.append(tool)
            self.tool_map[tool_name] = tool_schema
            
        logger.info(f"Loaded {len(self.tools)} tools from MCP server")
    
    # In client.py - Fix the result truncation in _execute_tool method
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]):
        """Execute an MCP tool with given arguments"""
        logger.info(f"Executing tool {tool_name} with args: {args}")
        
        # Display tool call (for "flashing" effect)
        tool_call_display = f"\n[🔧 Calling tool: {tool_name}]\n"
        tool_call_display += f"Parameters: {json.dumps(args, indent=2)}\n"
        print(tool_call_display)
        
        try:
            # Execute the tool using MCP session
            start_time = time.time()
            result = await self.session.call_tool(tool_name, args)
            execution_time = time.time() - start_time
            
            # Format and display result
            result_str = "".join(item.text for item in result.content if hasattr(item, 'text'))
            
            tool_result_display = "[📊 Tool result]:\n"
            # Remove the truncation limit and use a more controlled approach
            max_display_length = 5000  # Increased from 500
            if len(result_str) > max_display_length:
                # Show first and last parts with a clear separator
                first_part = result_str[:max_display_length//2]
                last_part = result_str[-max_display_length//2:]
                tool_result_display += f"{first_part}\n...\n[Middle content omitted for display]\n...\n{last_part}\n"
            else:
                tool_result_display += f"{result_str}\n"
            
            print(tool_result_display)
            
            # Update conversation context based on tool execution
            self._update_context_from_tool(tool_name, args, result_str)
            
            # Return the full result string - no truncation for Claude
            return result_str
            
        except Exception as e:
            error_message = f"❌ Error executing tool {tool_name}: {str(e)}"
            print(error_message)
            return error_message
    # In client.py - Add a function to validate email addresses before sending
    def _validate_email(self, email: str) -> tuple[bool, str]:
        """
        Validate if an email is properly formatted and exists in the system.
        Returns (is_valid, corrected_email_or_error_message)
        """
        # Basic format validation
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.match(email_pattern, email):
            return False, f"Invalid email format: {email}"
        
        # Check known domains for typos
        domain = email.split('@')[1]
        common_domains = ["gmail.com", "yahoo.com", "my.unt.edu", "organization.com"]
        for correct_domain in common_domains:
            if domain.lower() != correct_domain and get_close_matches(domain.lower(), [correct_domain], n=1, cutoff=0.75):
                corrected_email = email.replace(domain, correct_domain)
                return True, corrected_email
                
        # If no corrections needed, return the original email
        return True, email
    
    # ... [rest of the existing code] ...
    def _update_context_from_tool(self, tool_name: str, args: Dict[str, Any], result_str: str):
        """Update the conversation context based on tool execution results"""
        try:
            # Parse the result if it's JSON
            try:
                result_data = json.loads(result_str)
            except:
                result_data = None
                
            # Update context based on tool type
            if tool_name == "get_incident_details" and "incident_id" in args:
                if result_data and not result_data.get("error"):
                    self.chat_context["current_incident"] = {
                        "id": args["incident_id"],
                        "details": result_data
                    }
                    
            elif tool_name == "create_incident":
                if result_data and not result_data.get("error"):
                    if isinstance(result_data, dict) and "id" in result_data:
                        self.chat_context["current_incident"] = {
                            "id": result_data["id"],
                            "details": result_data,
                            "created_at": datetime.now().isoformat()
                        }
                    
            elif tool_name == "update_incident" and "incident_id" in args:
                if result_data and not result_data.get("error"):
                    # If we have this incident in context, update it
                    if self.chat_context["current_incident"] and self.chat_context["current_incident"]["id"] == str(args["incident_id"]):
                        self.chat_context["current_incident"]["details"] = result_data
                        self.chat_context["current_incident"]["last_updated"] = datetime.now().isoformat()
                        
            # Track problem creation and updates
            elif tool_name == "create_problem":
                if result_data and not result_data.get("error"):
                    if isinstance(result_data, dict) and "id" in result_data:
                        self.chat_context["current_problem"] = {
                            "id": result_data["id"],
                            "details": result_data,
                            "created_at": datetime.now().isoformat()
                        }
                        
            # Track search results to help with context
            elif tool_name.startswith("search_"):
                if result_data and not isinstance(result_data, dict):
                    self.chat_context[f"last_{tool_name}_results"] = {
                        "count": len(result_data) if isinstance(result_data, list) else 0,
                        "timestamp": datetime.now().isoformat()
                    }
        except Exception as e:
            logger.error(f"Error updating context from tool: {e}")

    def _clean_and_correct_query(self, query: str) -> str:
        """
        Apply fuzzy matching, error correction, and intent mapping to the user query.
        This helps handle minor spelling errors, typos, and conversational language.
        """
        cleaned_query = query.strip()
        
        # Store corrections for display
        corrections = []
        state_mappings = {
                            "assigned": "In Progress",
                            "in-progress": "In Progress", 
                            "inprogress": "In Progress",
                            "in_progress": "In Progress",
                            "in progress": "In Progress",  # Added explicit space mapping
                            "open": "Open",
                            "new": "New",
                            "pending": "Pending",
                            "resolved": "Resolved",
                            "closed": "Closed",
                            "done": "Closed",
                            "completed": "Closed",
                            "finished": "Closed"
                        }
        
        for state_term, formal_state in state_mappings.items():
        # Look for patterns like "state=assigned", "state is assigned", "state assigned"
            patterns = [
                f"state\\s*=\\s*{state_term}",
                f"state\\s+is\\s+{state_term}",
                f"state\\s+{state_term}",
                f"status\\s*=\\s*{state_term}",
                f"status\\s+is\\s+{state_term}",
                f"status\\s+{state_term}",
                f"tickets\\s+with\\s+state\\s+{state_term}",  # Added pattern for "tickets with state X"
                f"incidents\\s+with\\s+state\\s+{state_term}"  # Added pattern for "incidents with state X"
            ]
            for pattern in patterns:
                if re.search(pattern, cleaned_query, re.IGNORECASE):
                    old_query = cleaned_query
                    cleaned_query = re.sub(pattern, f"state=\"{formal_state}\"", cleaned_query, flags=re.IGNORECASE)
                    if old_query != cleaned_query:
                        corrections.append(f"'{state_term}' → '{formal_state}' (state)")
        # Function to find and replace misspelled terms
        def replace_misspelled(text, term_list, threshold=0.75):
            words = re.findall(r'\b\w+\b', text)
            for word in words:
                if word.lower() not in [t.lower() for t in term_list]:
                    matches = get_close_matches(word.lower(), [t.lower() for t in term_list], n=1, cutoff=threshold)
                    if matches:
                        best_match_index = [t.lower() for t in term_list].index(matches[0])
                        correct_term = term_list[best_match_index]
                        if word != correct_term:
                            old_text = text
                            # Replace with correct casing
                            pattern = re.compile(re.escape(word), re.IGNORECASE)
                            text = pattern.sub(correct_term, text, 1)
                            if old_text != text:
                                corrections.append(f"'{word}' → '{correct_term}'")
            return text
        
        # Handle intent mapping for states
        for state_term, formal_state in self.intent_mappings["states"].items():
            # Look for patterns like "state=assigned", "state is assigned", "state assigned"
            patterns = [
                f"state\\s*=\\s*{state_term}",
                f"state\\s+is\\s+{state_term}",
                f"state\\s+{state_term}",
                f"status\\s*=\\s*{state_term}",
                f"status\\s+is\\s+{state_term}",
                f"status\\s+{state_term}"
            ]
            
            for pattern in patterns:
                if re.search(pattern, cleaned_query, re.IGNORECASE):
                    old_query = cleaned_query
                    cleaned_query = re.sub(pattern, f"state=\"{formal_state}\"", cleaned_query, flags=re.IGNORECASE)
                    if old_query != cleaned_query:
                        corrections.append(f"'{state_term}' → '{formal_state}' (state)")
        
        # Handle intent mapping for priorities
        for priority_term, formal_priority in self.intent_mappings["priorities"].items():
            # Look for patterns like "priority=high", "priority is high", "high priority"
            patterns = [
                f"priority\\s*=\\s*{priority_term}",
                f"priority\\s+is\\s+{priority_term}",
                f"priority\\s+{priority_term}",
                f"{priority_term}\\s+priority"
            ]
            
            for pattern in patterns:
                if re.search(pattern, cleaned_query, re.IGNORECASE):
                    old_query = cleaned_query
                    cleaned_query = re.sub(pattern, f"priority=\"{formal_priority}\"", cleaned_query, flags=re.IGNORECASE)
                    if old_query != cleaned_query:
                        corrections.append(f"'{priority_term}' → '{formal_priority}' (priority)")
        
        # Handle entity mappings
        for entity_term, formal_entity in self.intent_mappings["entities"].items():
            if re.search(r'\b' + re.escape(entity_term) + r'\b', cleaned_query, re.IGNORECASE):
                old_query = cleaned_query
                cleaned_query = re.sub(r'\b' + re.escape(entity_term) + r'\b', formal_entity, cleaned_query, flags=re.IGNORECASE)
                if old_query != cleaned_query:
                    corrections.append(f"'{entity_term}' → '{formal_entity}'")
        
        # Correct common misspellings in query
        for category, terms in self.common_terms.items():
            cleaned_query = replace_misspelled(cleaned_query, terms)
        
        # Correct email addresses with common typos
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, cleaned_query)
        for email in emails:
            if '@' in email:
                # Check common email domain typos
                domain = email.split('@')[1]
                common_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]
                for correct_domain in common_domains:
                    if domain.lower() != correct_domain and get_close_matches(domain.lower(), [correct_domain], n=1, cutoff=0.75):
                        corrected_email = email.replace(domain, correct_domain)
                        cleaned_query = cleaned_query.replace(email, corrected_email)
                        corrections.append(f"'{email}' → '{corrected_email}'")
                        break
        
        # Special handling for specific queries
        if "assigned" in cleaned_query.lower() and "state" not in cleaned_query.lower():
            # If someone asks about "assigned incidents" without specifying state
            if any(term in cleaned_query.lower() for term in ["incident", "incidents", "ticket", "tickets"]):
                old_query = cleaned_query
                cleaned_query = cleaned_query + " with state=\"In Progress\""
                corrections.append(f"Added 'with state=\"In Progress\"' to query about assigned incidents")
        if "ticket" in cleaned_query.lower() and "incident" not in cleaned_query.lower():
            old_query = cleaned_query
            cleaned_query = cleaned_query.lower().replace("ticket", "incident")
            corrections.append(f"'ticket' → 'incident'")

        # Display corrections to the user if any were made
        if corrections:
            print("\n🔍 Applied corrections and interpretations:")
            for correction in corrections:
                print(f"  - {correction}")
        
        return cleaned_query

    async def process_query_with_langchain(self, query: str) -> str:
        """Process a query using LangChain, Anthropic Claude, and available SolarWinds tools"""
        if not self.session:
            logger.error("Session not initialized")
            return "Error: Not connected to server. Please restart the client."
        
        # Clean and correct the query
        cleaned_query = self._clean_and_correct_query(query)
        
        # Prepare the input for LangChain
        print("\n🔄 Thinking...")
        
        try:
            # Add the query to memory
            langchain_input = {
                "input": cleaned_query,
                "chat_history": self.memory.load_memory_variables({})["chat_history"]
            }
            
            # Define system message to help guide Claude with more context understanding
            system_message = SystemMessage(
                    content=(
                        "You are an AI assistant for SolarWinds Service Desk that understands user intent and context deeply. "
                        "You have access to various tools for interacting with the Service Desk API. "
                        "\n\n"
                        "IMPORTANT: Format your responses EXACTLY as shown in this template:"
                        "\n"
                        "**Response X:**\n"
                        "I'll [action] the [object].\n"
                        "\n"
                        "Then show the details of what you're doing, including tool calls and their results."
                        "End with a clear summary of what was accomplished and next steps if appropriate."
                        "\n\n"
                        "Always use the numbered response format (replace X with the appropriate number)."
                        "Maintain continuity with previous actions and reference objects by their names and IDs."
                        "Always respond in first person, not third person."
                        "Every response MUST start with '**Response X:**' where X is the response number."
                    )
                )
            
            # Prepare tool specifications for Claude
            claude_tools = []
            for tool in self.tools:
                tool_schema = self.tool_map.get(tool.name, {})
                claude_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool_schema
                })
            
            # Get history from memory
            history = self.memory.load_memory_variables({}).get("chat_history", [])
            
            # Convert history to appropriate format for Claude API with improved context handling
            claude_messages = []
            
            # We'll use the system message as a top-level parameter, not in the messages array
            system_prompt = system_message.content
            
            # Add conversation history
            tool_use_ids = set()  # Track tool use IDs to ensure proper pairing
            last_assistant_message = None
            
            for i, msg in enumerate(history):
                if isinstance(msg, HumanMessage):
                    claude_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    # Store current message and check if it contains tool_use
                    assistant_content = msg.content
                    
                    # Handle both string content and list content
                    if isinstance(assistant_content, str):
                        last_assistant_message = {"role": "assistant", "content": assistant_content}
                        claude_messages.append(last_assistant_message)
                    elif isinstance(assistant_content, list):
                        last_assistant_message = {"role": "assistant", "content": assistant_content}
                        claude_messages.append(last_assistant_message)
                        
                        # Extract tool_use_ids from this message for validation
                        for item in assistant_content:
                            if isinstance(item, dict) and item.get("type") == "tool_use":
                                tool_use_ids.add(item.get("id"))
                elif isinstance(msg, ToolMessage):
                    # Handle tool messages properly with proper pairing
                    if hasattr(msg, 'tool_use_id') and msg.tool_use_id:
                        claude_messages.append({
                            "role": "user", 
                            "content": [{"type": "tool_result", "tool_use_id": msg.tool_use_id, "content": [{"type": "text", "text": msg.content}]}]
                        })
                        # Mark this tool_use_id as handled
                        if msg.tool_use_id in tool_use_ids:
                            tool_use_ids.remove(msg.tool_use_id)
                    else:
                        # Fallback for tool messages without tool_use_id
                        claude_messages.append({"role": "user", "content": f"Tool result: {msg.content}"})
            
            # Generate a comprehensive context enhancement
            context_summary = self._enhance_history_for_context()
            
            # Format it as an additional context note
            if context_summary:
                context_enhancement = f"\n\nContext note: {context_summary}"
            else:
                context_enhancement = ""
            
            # Add the enhanced query with context
            enhanced_query = f"{cleaned_query}{context_enhancement}"
            
            # Log the enhanced query for debugging
            logger.debug(f"Enhanced query: {enhanced_query}")
            
            # Add the enhanced query to the messages
            claude_messages.append({"role": "user", "content": enhanced_query})
            
            # Initialize variables to track retries
            max_retries = 2
            retry_count = 0
            retry_backoff = 1.5
            
            while retry_count <= max_retries:
                try:
                    # Create the Claude API call
                    response = self.anthropic.messages.create(
                        model="claude-3-5-haiku-20241022",
                        max_tokens=1500,
                        system=system_prompt,
                        messages=claude_messages,
                        tools=claude_tools,
                        temperature=0.3
                    )
                    
                    # Parse and process the response
                    final_text = []
                    assistant_response = []
                    
                    for content in response.content:
                        if content.type == 'text':
                            final_text.append(content.text)
                            assistant_response.append(content)
                        elif content.type == 'tool_use':
                            tool_name = content.name
                            tool_args = content.input
                            tool_id = content.id
                            
                            # Validate and correct email addresses in tool args if present
                            if tool_name == "create_incident" and tool_args.get("requester_email"):
                                is_valid, corrected_email = self._validate_email(tool_args["requester_email"])
                                if not is_valid:
                                    # Use a default email if the provided one is invalid
                                    logger.warning(f"Invalid requester email: {tool_args['requester_email']}. Using fallback email.")
                                    tool_args["requester_email"] = "service.desk@organization.com"
                                else:
                                    # Use the possibly corrected email
                                    if corrected_email != tool_args["requester_email"]:
                                        logger.info(f"Corrected email from {tool_args['requester_email']} to {corrected_email}")
                                        tool_args["requester_email"] = corrected_email
                            
                            # Similar check for assignee_email
                            if tool_args.get("assignee_email"):
                                is_valid, corrected_email = self._validate_email(tool_args["assignee_email"])
                                if not is_valid:
                                    # Remove invalid assignee_email instead of using a default
                                    logger.warning(f"Invalid assignee email: {tool_args['assignee_email']}. Removing from request.")
                                    tool_args.pop("assignee_email")
                                else:
                                    if corrected_email != tool_args["assignee_email"]:
                                        logger.info(f"Corrected email from {tool_args['assignee_email']} to {corrected_email}")
                                        tool_args["assignee_email"] = corrected_email
                            
                            try:
                                # Use the _execute_tool method to run the tool with enhanced result handling
                                result = await self._execute_tool(tool_name, tool_args)
                                
                                # If we had successful tool execution, update the Claude messages sequence
                                claude_messages.append({"role": "assistant", "content": [content]})
                                claude_messages.append({
                                    "role": "user", 
                                    "content": [
                                        {
                                            "type": "tool_result", 
                                            "tool_use_id": tool_id, 
                                            "content": [{"type": "text", "text": result}]
                                        }
                                    ]
                                })
                                
                                # Get the next response from Claude with retry handling
                                print("🔄 Processing results...")
                                follow_up_retries = 0
                                max_follow_up_retries = 2
                                
                                while follow_up_retries <= max_follow_up_retries:
                                    try:
                                        follow_up_response = self.anthropic.messages.create(
                                            model="claude-3-5-haiku-20241022",
                                            max_tokens=1500,
                                            system=system_prompt,
                                            messages=claude_messages,
                                            tools=claude_tools,
                                            temperature=0.3
                                        )
                                        
                                        # Add the follow-up response to final text
                                        for content_item in follow_up_response.content:
                                            if content_item.type == 'text':
                                                final_text.append(content_item.text)
                                                assistant_response.append(content_item)
                                        
                                        # If we get here, break the retry loop
                                        break
                                        
                                    except Exception as e:
                                        follow_up_retries += 1
                                        if "rate limit" in str(e).lower() or "429" in str(e):
                                            # Apply exponential backoff
                                            wait_time = retry_backoff ** follow_up_retries
                                            logger.warning(f"Rate limited on follow-up. Retrying in {wait_time}s...")
                                            await asyncio.sleep(wait_time)
                                            
                                            if follow_up_retries > max_follow_up_retries:
                                                error_message = "Rate limit reached. Please try again later."
                                                final_text.append(error_message)
                                        else:
                                            # For other errors, log and continue
                                            logger.error(f"Error in follow-up response: {e}", exc_info=True)
                                            error_message = f"❌ Error processing results: {str(e)}"
                                            final_text.append(error_message)
                                            break
                                
                            except Exception as e:
                                logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                                error_message = f"❌ Error executing tool {tool_name}: {str(e)}"
                                final_text.append(error_message)
                                
                                # Add the error message to the Claude messages sequence
                                claude_messages.append({"role": "assistant", "content": [content]})
                                claude_messages.append({
                                    "role": "user", 
                                    "content": [
                                        {
                                            "type": "tool_result", 
                                            "tool_use_id": tool_id, 
                                            "content": [{"type": "text", "text": error_message}]
                                        }
                                    ]
                                })
                    
                    # Break the retry loop if we get here
                    break
                    
                except Exception as e:
                    retry_count += 1
                    if "rate limit" in str(e).lower() or "429" in str(e):
                        # Apply exponential backoff
                        wait_time = retry_backoff ** retry_count
                        logger.warning(f"Rate limited. Retrying in {wait_time}s... (Attempt {retry_count}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        
                        if retry_count > max_retries:
                            return "I apologize, but I've hit a rate limit. Please try again in a moment."
                    else:
                        # For other errors, log and return error message
                        logger.error(f"Error in Claude API call: {e}", exc_info=True)
                        return f"I encountered an issue processing your request. This might be due to a temporary API limitation. Please try again with a more specific query."
            
            # Format the response appropriately
            output_text = self._format_response("\n".join(final_text))
            
            # Check for empty or very short responses that might indicate an issue
            if len(output_text.strip()) < 20:
                logger.warning(f"Suspiciously short response: '{output_text}'")
                output_text += "\n\nNote: The response was unusually brief. If this doesn't answer your question, please try rephrasing your query or check if there might be a connection issue."
            
            # Check for truncation indicators and add clarification
            if "[Result truncated" in output_text:
                output_text = output_text.replace(
                    "[Result truncated, full data sent to Claude]",
                    "[Partial results shown here, but the complete data was processed]"
                )
            
            # Update memory with the latest exchange
            self.memory.save_context({"input": cleaned_query}, {"output": output_text})
            
            # Return the final response text
            return output_text
            
        except Exception as e:
            logger.error(f"Error processing query with LangChain: {e}", exc_info=True)
            error_trace = traceback.format_exc()
            logger.debug(f"Full error traceback: {error_trace}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again or consider simplifying your query."
        
# In client.py - Enhance the format_response function
    def _format_response(self, text: str) -> str:
        """Format the response to consistently match the required output style"""
        
        # Add consistent formatting to the response
        formatted_text = text.strip()
        
        # Add numbered prefix
        history = self.memory.load_memory_variables({}).get("chat_history", [])
        ai_message_count = sum(1 for msg in history if isinstance(msg, AIMessage))
        
        response_number = ai_message_count + 1
        
        # Always enforce the response format
        if not formatted_text.startswith(f"**Response {response_number}:**"):
            if "**Response" in formatted_text:
                # If there's already a response heading, update the number
                formatted_text = re.sub(r'\*\*Response \d+:\*\*', f'**Response {response_number}:**', formatted_text, 1)
            else:
                # Add the proper format
                formatted_text = f"**Response {response_number}:**\n{formatted_text}"
        
        # Ensure there's a proper summary/closure
        if not any(phrase in formatted_text.lower() for phrase in [
            "successfully", "completed", "updated", "created", "summary", 
            "has been", "is now", "the incident", "the following"
        ]):
            # Add a summary closure if it doesn't seem to have one
            formatted_text += "\n\nThis completes the requested operation."
        
        return formatted_text
        # # Check if response contains truncated results and add a note
        # if "[Result truncated" in formatted_text:
        #     formatted_text += "\n\n**Note:** Some results were truncated for display. The full data was processed and analyzed correctly."
        
        # # Ensure the response has a good closing
        # if not any(phrase in formatted_text.lower() for phrase in [
        #     "successfully", "completed", "updated", "created", "summary", 
        #     "has been", "is now", "the incident", "the following"
        # ]):
        #     # Add a summary closure if it doesn't seem to have one
        #     formatted_text += "\n\nThis completes the requested operation."
        
        # return formatted_text
    
    def _enhance_history_for_context(self):
        """Create an enhanced history summary to provide better context to Claude"""
        history = self.memory.load_memory_variables({}).get("chat_history", [])
        
        # Create a condensed history summary
        summary = []
        
        # Extract key information from previous interactions
        incident_mentions = []
        problem_mentions = []
        user_mentions = []
        actions_taken = []
        
        for i, msg in enumerate(history):
            if isinstance(msg, HumanMessage):
                # Look for entities in user messages
                text = msg.content.lower()
                
                # Extract incident IDs
                incident_matches = re.findall(r'incident #?(\d+)', text)
                incident_mentions.extend(incident_matches)
                
                # Extract problem IDs
                problem_matches = re.findall(r'problem #?(\d+)', text)
                problem_mentions.extend(problem_matches)
                
                # Extract user mentions
                user_matches = re.findall(r'user [\'\"]?([^\'\"]+)[\'\"]?', text)
                user_mentions.extend(user_matches)
                
            elif isinstance(msg, AIMessage):
                # Look for actions in AI messages
                text = msg.content.lower()
                
                # Extract key actions
                if "updated" in text:
                    action = "update"
                elif "created" in text:
                    action = "create"
                elif "resolved" in text:
                    action = "resolve"
                elif "searched" in text:
                    action = "search"
                else:
                    action = None
                    
                if action:
                    # Determine the target of the action
                    if "incident" in text:
                        target = "incident"
                    elif "problem" in text:
                        target = "problem"
                    elif "comment" in text:
                        target = "comment"
                    elif "user" in text:
                        target = "user"
                    else:
                        target = "item"
                        
                    actions_taken.append(f"{action} {target}")
        
        # Create context summary
        if incident_mentions:
            summary.append(f"Previously discussed incidents: {', '.join('#' + id for id in set(incident_mentions))}")
            
        if problem_mentions:
            summary.append(f"Previously discussed problems: {', '.join('#' + id for id in set(problem_mentions))}")
            
        if user_mentions:
            summary.append(f"Referenced users: {', '.join(set(user_mentions))}")
            
        if actions_taken:
            summary.append(f"Previous actions: {', '.join(actions_taken[-3:])}")
            
        # Add current context
        if self.chat_context["current_incident"]:
            incident_id = self.chat_context["current_incident"]["id"]
            incident_details = self.chat_context["current_incident"].get("details", {})
            if incident_details:
                incident_name = incident_details.get("name", "Unknown")
                incident_state = incident_details.get("state", "Unknown")
                summary.append(f"Current focus: Incident #{incident_id} '{incident_name}' (State: {incident_state})")
        
        if self.chat_context["current_problem"]:
            problem_id = self.chat_context["current_problem"]["id"]
            problem_details = self.chat_context["current_problem"].get("details", {})
            if problem_details:
                problem_name = problem_details.get("name", "Unknown")
                summary.append(f"Related problem: Problem #{problem_id} '{problem_name}'")
        
            return "\n".join(summary)

    async def chat_loop(self):
        """Run an interactive chat loop for SolarWinds Service Desk"""
        print("\n✨ SolarWinds Service Desk Client Started! ✨")
        print("You can ask questions about tickets, users, departments, etc.")
        print("Type 'quit' to exit.")
        
        # Display API mode status
        if os.getenv("SOLARWINDS_API_TOKEN"):
            print("\n🔑 Running with API token - Connected to live SolarWinds Service Desk")
        else:
            print("\n⚠️ No API token found - Running in DEMO mode with simulated responses")
        
        # Display some example queries
        print("\nExample queries you can try:")
        print("- Show me open incidents")
        print("- Create a new incident for network outage")
        print("- Search for users in the IT department")
        print("- What are the active alerts in the system?")
        print("- Analyze incidents for last month")
        
        # Track user question numbers
        question_counter = 0
        
        while True:
            try:
                # Increment question counter for each new user input
                question_counter += 1
                
                # Format the prompt with question number
                query = input(f"\n**User Question {question_counter}:**\n").strip()
                
                if not query:
                    question_counter -= 1  # Don't count empty queries
                    continue
                    
                if query.lower() in ['quit', 'exit']:
                    logger.info("User requested exit")
                    print("\n👋 Goodbye!")
                    break
                
                print("\n🔄 Processing your request...")
                
                # Add a timeout for processing to avoid hanging
                try:
                    response = await asyncio.wait_for(
                        self.process_query_with_langchain(query),
                        timeout=60.0  # 60-second timeout
                    )
                    print(f"\n{response}")
                    
                except asyncio.TimeoutError:
                    logger.error("Request processing timed out")
                    print("\n⚠️ The request took too long to process. This might be due to API latency or complexity of the query.")
                    print("Please try again with a simpler query or check your connection.")
                
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt detected")
                print("\n👋 Exiting...")
                break
            except Exception as e:
                logger.error(f"Error in chat loop: {e}", exc_info=True)
                print(f"\n❌ Error: {str(e)}")
                print("Please try again or restart the client if issues persist.")
        
    async def cleanup(self):
        """Clean up resources"""
        try:
            logger.info("Cleaning up resources")
            await self.exit_stack.aclose()
            logger.info("Cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            print(f"\n⚠️ Warning: Failed to clean up some resources: {str(e)}")

async def main():
    print("\n🌟 SolarWinds MCP Client 🌟")
    
    if len(asyncio.get_event_loop()._ready) > 0:
        # Reset the event loop if it's been used
        asyncio.set_event_loop(asyncio.new_event_loop())
        
    import sys
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        print("\nExample:")
        print("  python client.py server.py")
        print("  python client.py /full/path/to/server.py")
        sys.exit(1)
        
    server_path = sys.argv[1]
    
    # Get the absolute path
    server_path = os.path.abspath(server_path)
    logger.info(f"Using server path: {server_path}")
        
    client = SolarWindsClient()
    try:
        await client.connect_to_server(server_path)
        await client.chat_loop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {str(e)}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())