# # Modify the imports section at the top of conversational_client.py
# import asyncio
# import json
# import os
# import sys
# from contextlib import AsyncExitStack
# from typing import Dict, List, Optional, Any
# from dotenv import load_dotenv


# # MCP
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client

# # Anthropic (for Claude)
# import anthropic
# from anthropic import Anthropic

# load_dotenv()  # Load environment variables, including ANTHROPIC_API_KEY, etc.

# class ConversationalClient:
#     def __init__(self, server_path):
#         self.server_path = server_path
#         self.exit_stack = AsyncExitStack()
#         self.session = None
#         self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
#         self.conversation = []  # Store conversation messages
#         self.cached_prompts = {}  # Store info about cached prompts
#         self.server_tools = []  # Store available MCP tools
        
#         # Default system prompt
#         self.default_system_prompt = """
# You are an IT Service Desk Assistant powered by Claude, connected to a SolarWinds Service Desk system.
# You can help users by accessing real-time data, creating and updating tickets, and providing support.
# Always use a natural, helpful tone and provide clear, concise answers.

# When asked a question, you should:
# 1. Determine if you need to use SolarWinds tools to answer
# 2. Call any necessary tools to gather information
# 3. Present your response in a clear, natural way

# You have access to various tools including incident management, user management, departments, and more.
# """

#     async def connect_server(self):
#         """Spawn the MCP server via stdio and initialize the session."""
#         server_params = StdioServerParameters(
#             command="python",
#             args=[self.server_path],
#             env=os.environ
#         )
#         transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
#         self.stdio, self.write = transport

#         self.session = await self.exit_stack.enter_async_context(
#             ClientSession(self.stdio, self.write)
#         )
#         await self.session.initialize()

#         # List available tools from the server
#         tools_info = await self.session.list_tools()
#         self.server_tools = tools_info.tools
#         print("Connected to MCP server. Available tools:")
#         for t in self.server_tools:
#             print(f" - {t.name}")
            
#         # Load cached prompts
#         await self.load_cached_prompts()

#     async def load_cached_prompts(self):
#         """Load cached prompts from the server"""
#         try:
#             result = await self.session.call_tool("list_cached_prompts", {})
#             if result.content:
#                 prompts_data = json.loads(result.content[0].text)
#                 self.cached_prompts = prompts_data.get("cached_prompts", {})
#                 print(f"Loaded {len(self.cached_prompts)} cached prompts")
#         except Exception as e:
#             print(f"Error loading cached prompts: {e}")

#     async def close(self):
#         await self.exit_stack.aclose()

#     async def chat_loop(self):
#         """
#         Natural language conversation loop.
#         Uses prompt caching for improved efficiency.
#         """
#         # Initialize with the system prompt cached for efficiency
#         await self.ensure_system_prompt_cached()
        
#         print("\nWelcome to the SolarWinds Service Desk Assistant!")
#         print("Ask questions in natural language to get information or perform tasks.")
#         print("Type 'quit' to exit.\n")
        
#         while True:
#             user_input = input("You: ").strip()
#             if user_input.lower() == "quit":
#                 break
                
#             # Process the user query
#             response = await self.process_query(user_input)
#             print(f"Assistant: {response}")
    
#     async def ensure_system_prompt_cached(self):
#         """Ensure the default system prompt is cached for efficiency"""
#         if "default_system" not in self.cached_prompts:
#             try:
#                 result = await self.session.call_tool("cache_prompt", {
#                     "prompt_name": "default_system", 
#                     "prompt_content": self.default_system_prompt,
#                     "model": "claude-3-haiku-20240307"
#                 })
#                 if result.content:
#                     response = json.loads(result.content[0].text)
#                     if response.get("status") == "success":
#                         print("System prompt cached successfully")
#                         await self.load_cached_prompts()  # Reload cache
#             except Exception as e:
#                 print(f"Error caching system prompt: {e}")
    
#     async def process_query(self, user_query: str):
#         """
#         Process a natural language query using Claude and MCP tools
#         """
#         # Add user query to conversation history
#         self.conversation.append({"role": "user", "content": user_query})
        
#         # First, have Claude understand the query and determine if tools are needed
#         planning_response = await self.plan_query_execution(user_query)
        
#         # If tools are needed, execute them and then have Claude generate final response
#         if planning_response.get("needs_tools", False):
#             tools_to_use = planning_response.get("tools_to_use", [])
#             tool_results = await self.execute_tools(tools_to_use)
            
#             # Generate final response with tool results
#             final_response = await self.generate_final_response(user_query, planning_response, tool_results)
#             self.conversation.append({"role": "assistant", "content": final_response})
#             return final_response
#         else:
#             # Simple query that doesn't need tools
#             simple_response = planning_response.get("response", "I'm not sure how to help with that.")
#             self.conversation.append({"role": "assistant", "content": simple_response})
#             return simple_response
    
#     # Fix for the plan_query_execution method in conversational_client.py

#     async def plan_query_execution(self, user_query: str):
#         """
#         Have Claude understand what tools are needed to answer the query
#         """
#         try:
#             # Format all available tools for Claude
#             tools_description = "\n".join([
#                 f"- {tool.name}: {tool.description}" 
#                 for tool in self.server_tools
#             ])
            
#             planning_prompt = f"""
#     You are helping a user interact with a SolarWinds Service Desk system.
#     Based on their query, determine if you need to use any tools to respond. The tools available are:

#     {tools_description}

#     User query: "{user_query}"

#     First, think about whether any tools are needed to answer this query properly.
#     If tools are needed, identify:
#     1. Which specific tools should be used
#     2. What parameters to use for each tool
#     3. The order in which to call the tools

#     Return your thoughts in this JSON structure:
#     {{
#     "needs_tools": true/false,
#     "tools_to_use": [
#         {{
#         "tool_name": "name_of_tool",
#         "parameters": {{"param1": "value1", "param2": "value2"}}
#         }}
#     ],
#     "reasoning": "Explanation for why these tools are needed and how they'll be used",
#     "response": "A direct response if no tools are needed"
#     }}
#     """
            
#             # Use cached system prompt if available, otherwise create a new message
#             if "planning_prompt" in self.cached_prompts:
#                 result = await self.session.call_tool("use_cached_prompt", {
#                     "prompt_name": "planning_prompt", 
#                     "message": planning_prompt + "\n\n" + user_query,
#                     "max_tokens": 1500
#                 })
                
#                 if result.content and result.content[0].text:
#                     try:
#                         return json.loads(result.content[0].text)
#                     except:
#                         # If not valid JSON, create a basic response
#                         return {
#                             "needs_tools": False,
#                             "response": "I'm having trouble understanding how to process this query. Could you rephrase it?"
#                         }
#             else:
#                 # Cache the planning prompt for future use
#                 await self.session.call_tool("cache_prompt", {
#                     "prompt_name": "planning_prompt", 
#                     "prompt_content": planning_prompt,
#                     "model": "claude-3-haiku-20240307"
#                 })
                
#                 # Create a regular message - Fix begins here - use asyncio.to_thread
#                 try:
#                     response = await asyncio.to_thread(
#                         self.anthropic.messages.create,
#                         model="claude-3-haiku-20240307",
#                         max_tokens=1500,
#                         system=planning_prompt,
#                         messages=[{"role": "user", "content": user_query}]
#                     )
                    
#                     try:
#                         return json.loads(response.content[0].text)
#                     except:
#                         return {
#                             "needs_tools": False,
#                             "response": "I'm having trouble understanding how to process this query. Could you rephrase it?"
#                         }
#                 except Exception as e:
#                     print(f"Error creating message: {e}")
#                     return {
#                         "needs_tools": False,
#                         "response": "I encountered an error processing your request. Please try again."
#                     }
                
#         except Exception as e:
#             print(f"Error in planning query execution: {e}")
#             return {
#                 "needs_tools": False,
#                 "response": "I encountered an error while processing your query. Please try again."
#             }
    
#     async def execute_tools(self, tools_to_use):
#         """
#         Execute the specified MCP tools with parameters
#         """
#         tool_results = []
        
#         for tool_info in tools_to_use:
#             tool_name = tool_info.get("tool_name")
#             parameters = tool_info.get("parameters", {})
            
#             try:
#                 print(f"Executing tool: {tool_name} with parameters: {parameters}")
#                 result = await self.session.call_tool(tool_name, parameters)
                
#                 if result.content:
#                     try:
#                         # Try to parse as JSON first
#                         result_data = json.loads(result.content[0].text)
#                     except:
#                         # If not valid JSON, use raw text
#                         result_data = result.content[0].text
                    
#                     tool_results.append({
#                         "tool": tool_name,
#                         "parameters": parameters,
#                         "result": result_data
#                     })
#                     print(f"Tool execution successful: {tool_name}")
#                 else:
#                     tool_results.append({
#                         "tool": tool_name,
#                         "parameters": parameters,
#                         "result": "No result returned",
#                         "error": True
#                     })
#                     print(f"Tool execution returned no result: {tool_name}")
#             except Exception as e:
#                 tool_results.append({
#                     "tool": tool_name,
#                     "parameters": parameters,
#                     "error": str(e)
#                 })
#                 print(f"Error executing tool {tool_name}: {e}")
        
#         return tool_results
    
#     # Fix for the generate_final_response method in conversational_client.py

#     async def generate_final_response(self, user_query, planning_response, tool_results):
#         """
#         Generate final response using Claude based on tool results
#         Uses cached prompt for efficiency when possible
#         """
#         # Create a prompt for formatting the response
#         results_summary = json.dumps(tool_results, indent=2)
        
#         response_prompt = f"""
#     You are a helpful IT service desk assistant. Format a natural, conversational response to the user's query
#     based on the results from the SolarWinds Service Desk system.

#     Original user query: "{user_query}"

#     The reasoning and plan for answering this query:
#     {planning_response.get('reasoning', 'No reasoning provided')}

#     Results from executing the necessary tools:
#     {results_summary}

#     Important guidelines:
#     1. Present information in a clear, conversational way
#     2. Don't mention the technical details of how you retrieved the information
#     3. Don't mention "tools", "parameters", "API calls", etc.
#     4. Format any data in an easy-to-read way
#     5. If tool execution failed, handle it gracefully and explain what went wrong
#     6. Be concise but complete
#     7. If appropriate, suggest follow-up actions the user might want to take

#     Your response:
#     """

#         try:
#             # Check if response formatting prompt is cached
#             if "response_formatting" in self.cached_prompts:
#                 result = await self.session.call_tool("use_cached_prompt", {
#                     "prompt_name": "response_formatting", 
#                     "message": response_prompt,
#                     "max_tokens": 1500
#                 })
                
#                 if result.content:
#                     return result.content[0].text
#             else:
#                 # Cache the response formatting prompt for future use
#                 await self.session.call_tool("cache_prompt", {
#                     "prompt_name": "response_formatting", 
#                     "prompt_content": response_prompt,
#                     "model": "claude-3-haiku-20240307"
#                 })
                
#                 # Create a regular message - FIX: Use asyncio.to_thread
#                 try:
#                     response = await asyncio.to_thread(
#                         self.anthropic.messages.create,
#                         model="claude-3-haiku-20240307",
#                         max_tokens=1500,
#                         system=response_prompt,
#                         messages=[{"role": "user", "content": "Generate the response for the user"}]
#                     )
                    
#                     return response.content[0].text
#                 except Exception as e:
#                     print(f"Error creating message: {e}")
#                     return f"I found some information for you, but ran into an issue formatting it properly. Let me try again or rephrase your question."
                    
#         except Exception as e:
#             print(f"Error generating final response: {e}")
#             return f"I found some information for you, but ran into an issue formatting it: {str(e)}"  


#     async def create_specialized_prompts(self):
#         """
#         Create and cache specialized prompts for common use cases
#         """
#         specialized_prompts = {
#             "incident_analysis": """
# You are a specialized IT incident analyst. When analyzing incident data from the SolarWinds Service Desk,
# focus on:
# 1. Severity and impact assessment
# 2. Root cause identification
# 3. Resolution recommendations
# 4. Patterns with similar past incidents
# 5. Prevention measures

# Present your analysis in a clear, structured format with actionable recommendations.
# """,
#             "user_activity": """
# You are a specialized IT user activity analyst. When analyzing user data from the SolarWinds Service Desk,
# focus on:
# 1. Ticket submission patterns
# 2. Common issue categories
# 3. Resolution timeframes
# 4. Satisfaction metrics
# 5. Potential training needs

# Present your analysis in a helpful, empathetic manner with practical suggestions.
# """,
#             "department_metrics": """
# You are a specialized IT department metrics analyst. When analyzing department data from SolarWinds Service Desk,
# focus on:
# 1. Volume trends over time
# 2. Average resolution times
# 3. Satisfaction scores
# 4. Resource allocation efficiency
# 5. Improvement opportunities

# Present your analysis with visual-friendly descriptions and specific recommendations.
# """
#         }
        
#         # Cache each specialized prompt
#         for name, content in specialized_prompts.items():
#             try:
#                 result = await self.session.call_tool("cache_prompt", {
#                     "prompt_name": name,
#                     "prompt_content": content
#                 })
#                 if result.content:
#                     response = json.loads(result.content[0].text)
#                     if response.get("status") == "success":
#                         print(f"Cached specialized prompt: {name}")
#             except Exception as e:
#                 print(f"Error caching specialized prompt {name}: {e}")
    
#     async def process_command(self, command):
#         """
#         Process special commands starting with '/' 
#         """
#         parts = command.split()
#         cmd = parts[0].lower()
        
#         if cmd == "/help":
#             return """
#                     Available commands:
#                     /help - Show this help message
#                     /tools - List available SolarWinds tools
#                     /cache - List cached prompts
#                     /cache_prompt <name> <content> - Cache a new prompt
#                     /clear - Clear conversation history
#                     /batch <query1> | <query2> | ... - Run multiple queries in batch mode
#                     """
            
#         elif cmd == "/tools":
#             return "Available tools:\n" + "\n".join([
#                 f"- {tool.name}: {tool.description}" 
#                 for tool in self.server_tools
#             ])
            
#         elif cmd == "/cache":
#             try:
#                 result = await self.session.call_tool("list_cached_prompts", {})
#                 if result.content:
#                     prompts_data = json.loads(result.content[0].text)
#                     self.cached_prompts = prompts_data.get("cached_prompts", {})
#                     return f"Cached prompts ({len(self.cached_prompts)}):\n" + "\n".join(self.cached_prompts.keys())
#             except Exception as e:
#                 return f"Error listing cached prompts: {e}"
                
#         elif cmd == "/clear":
#             self.conversation = []
#             return "Conversation history cleared."
            
#         elif cmd == "/batch" and len(command) > 7:
#     # Process multiple queries in batch
#             batch_text = command[7:].strip()
#             queries = [q.strip() for q in batch_text.split("|") if q.strip()]
            
#             if not queries:
#                 return "No valid queries provided for batch processing."
                
#             try:
#                 result = await self.session.call_tool("batch_process_messages", {
#                     "messages": queries,
#                     "model": "claude-3-haiku-20240307"  # Fixed model name
#                 })
                
#                 if result.content:
#                     batch_results = json.loads(result.content[0].text)
                    
#                     if "results" in batch_results:
#                         formatted_results = []
#                         for i, res in enumerate(batch_results["results"]):
#                             formatted_results.append(f"Query {i+1}: {res['original_message']}\nResponse: {res['response']}\n")
                        
#                         return "Batch Processing Results:\n\n" + "\n".join(formatted_results)
#                     else:
#                         return f"Batch processing error: {batch_results.get('error', 'Unknown error')}"
#             except Exception as e:
#                 return f"Error in batch processing: {e}"
                
#         elif cmd.startswith("/cache_prompt") and len(parts) >= 3:
#             name = parts[1]
#             content = " ".join(parts[2:])
            
#             try:
#                 result = await self.session.call_tool("cache_prompt", {
#                     "prompt_name": name,
#                     "prompt_content": content
#                 })
                
#                 if result.content:
#                     response = json.loads(result.content[0].text)
#                     if response.get("status") == "success":
#                         return f"Successfully cached prompt: {name}"
#                     else:
#                         return f"Error caching prompt: {response.get('error', 'Unknown error')}"
#             except Exception as e:
#                 return f"Error caching prompt: {e}"
                
#         return "Unknown or invalid command. Type /help for available commands."

#     async def chat_loop(self):
#         """
#         Natural language conversation loop.
#         Uses prompt caching for improved efficiency.
#         """
#         # Initialize with system prompt and specialized prompts
#         await self.ensure_system_prompt_cached()
#         await self.create_specialized_prompts()
        
#         print("\nWelcome to the SolarWinds Service Desk Assistant!")
#         print("Ask questions in natural language to get information or perform tasks.")
#         print("Type '/help' for special commands or 'quit' to exit.\n")
        
#         while True:
#             user_input = input("You: ").strip()
#             if user_input.lower() == "quit":
#                 break
                
#             # Check if it's a special command
#             if user_input.startswith("/"):
#                 response = await self.process_command(user_input)
#                 print(f"Assistant: {response}")
#                 continue
                
#             # Process the user query
#             print("Processing your request...")
#             response = await self.process_query(user_input)
#             print(f"Assistant: {response}")

# # Update the main function
# async def main():
#     # Adjust path to your server.py
#     server_path = os.path.abspath("server.py")
    
#     print(f"Starting with server path: {server_path}")
#     if not os.path.exists(server_path):
#         print(f"Error: Server file not found at {server_path}")
#         sys.exit(1)

#     client = ConversationalClient(server_path)
#     try:
#         print("Connecting to server...")
#         await client.connect_server()
#         await client.chat_loop()
#     except Exception as e:
#         print(f"Error in main execution: {e}")
#     finally:
#         await client.close() 

# if __name__ == "__main__":
#     asyncio.run(main())