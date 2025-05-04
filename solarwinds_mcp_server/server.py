from typing import Any, Dict, List, Optional, Union
import os
import json
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from pydantic import AnyUrl
import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('solarwinds_server')

# Then add log statements at key points
# logger.debug("Server starting up")
# ... your existing code
# logger.debug("Initializing FastMCP server")
# ... your existing code
# logger.debug("Setting up tools")
# ... and so on

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("solarwinds-service-desk")

# Constants
API_TOKEN = os.getenv("SOLARWINDS_API_TOKEN")
# API_URL = os.getenv("SOLARWINDS_API_URL", "https://api.samanage.com")
# API_URL = os.getenv("SOLARWINDS_API_URL")
# API_URL = os.getenv("SOLARWINDS_API_URL")
API_URL = "https://universitytest.samanage.com"
API_VERSION = "v2.1"
HEADERS = {
    "X-Samanage-Authorization": f"Bearer {API_TOKEN}",
    "Accept": f"application/vnd.samanage.{API_VERSION}+json",
    "Content-Type": "application/json"
}

# Create HTTP client
async def get_client() -> httpx.AsyncClient:
    """Create and return an HTTP client with the configured headers."""
    if not API_TOKEN:
        logger.warning("SOLARWINDS_API_TOKEN not found in environment variables. Using demo mode.")
        # In demo mode, we'll still return a client but requests will fail gracefully
        
    return httpx.AsyncClient(
        base_url=API_URL,
        headers=HEADERS,
        timeout=30.0
    )

# Helper function to make API requests
# Improved helper function to make API requests
async def make_api_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Make a request to the SolarWinds Service Desk API with improved error handling.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method (GET, POST, PUT, DELETE)
        params: Query parameters
        data: Request body data
        
    Returns:
        Parsed JSON response
    """
    # Normalize the endpoint if needed
    if endpoint.startswith('/'):
        endpoint = endpoint[1:]
        
    # Gracefully handle empty parameters or data
    if params is not None:
        # Remove None values from params
        params = {k: v for k, v in params.items() if v is not None}
    
    # Clean up data if it exists, removing None values
    if data is not None:
        # Use a recursive function to clean the data
        def clean_dict(d):
            if not isinstance(d, dict):
                return d
            return {
                k: clean_dict(v) if isinstance(v, dict) else v
                for k, v in d.items()
                if v is not None
            }
        data = clean_dict(data)
    
    async with await get_client() as client:
        try:
            # Handle API Token not configured scenario
            if not API_TOKEN and not endpoint.startswith("test"):
                logger.warning(f"Simulating API call to {endpoint} (demo mode)")
                
                # Return mock data instead of making a real API call
                if endpoint.endswith("incidents.json"):
                    return [{"id": "123", "name": "Demo Incident", "state": "Open", "priority": "Medium"}]
                elif endpoint.endswith("users.json"):
                    return [{"id": "456", "name": "Demo User", "email": "demo@example.com"}]
                elif "incidents" in endpoint and ".json" in endpoint:
                    return {"id": "123", "name": "Demo Incident", "state": "Open", "priority": "Medium"}
                else:
                    return []
                    
            # Make the actual API call
            if method == "GET":
                response = await client.get(endpoint, params=params)
            elif method == "POST":
                response = await client.post(endpoint, json=data, params=params)
            elif method == "PUT":
                response = await client.put(endpoint, json=data, params=params)
            elif method == "DELETE":
                response = await client.delete(endpoint, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Improved error logging
            error_detail = f"API request failed: {e.response.status_code}"
            try:
                error_json = e.response.json()
                error_detail += f" - {json.dumps(error_json)}"
            except:
                error_detail += f" - {e.response.text}"
            
            logger.error(f"HTTP Error: {error_detail}")
            raise ValueError(error_detail)
        except httpx.RequestError as e:
            logger.error(f"Network error: {str(e)}")
            raise ValueError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error making API request: {str(e)}")
            raise ValueError(f"Error making API request: {str(e)}")
# Resources - API Entry Points
@mcp.resource("samanage://api")
async def get_api_endpoints() -> str:
    """Get list of available API endpoints."""
    response = await make_api_request("api.json")
    return json.dumps(response, indent=2)

# Incidents Resources
@mcp.resource("samanage://incidents")
async def get_incidents() -> str:
    """Get list of all incidents."""
    response = await make_api_request("incidents.json")
    return json.dumps(response, indent=2)

@mcp.resource("samanage://incidents/{id}")
async def get_incident(id: str) -> str:
    """Get detailed information about a specific incident."""
    response = await make_api_request(f"incidents/{id}.json")
    return json.dumps(response, indent=2)
    
@mcp.tool()
async def get_incident_details(
    incident_id: Union[str, int]
) -> str:
    """
    Get detailed information about a specific incident by ID.
    
    Args:
        incident_id: ID of the incident to retrieve
    """
    incident_id_str = ensure_string_id(incident_id)
    try:
        response = await make_api_request(f"incidents/{incident_id_str}.json")
        return json.dumps(response, indent=2)
    except ValueError as e:
        error_msg = str(e)
        if "404" in error_msg:
            return json.dumps({
                "error": f"Incident with ID {incident_id} not found. Please verify the incident ID and try again.",
                "details": error_msg
            }, indent=2)
        return json.dumps({
            "error": "Error retrieving incident details",
            "details": error_msg
        }, indent=2)

# Problems Resources
@mcp.resource("samanage://problems")
async def get_problems() -> str:
    """Get list of all problems."""
    response = await make_api_request("problems.json")
    return json.dumps(response, indent=2)

@mcp.resource("samanage://problems/{id}")
async def get_problem(id: str) -> str:
    """Get detailed information about a specific problem."""
    response = await make_api_request(f"problems/{id}.json")
    return json.dumps(response, indent=2)

# Users Resources
@mcp.resource("samanage://users")
async def get_users() -> str:
    """Get list of all users."""
    response = await make_api_request("users.json")
    return json.dumps(response, indent=2)

@mcp.resource("samanage://users/{id}")
async def get_user(id: str) -> str:
    """Get detailed information about a specific user."""
    response = await make_api_request(f"users/{id}.json")
    return json.dumps(response, indent=2)

# Implement more resources for other endpoints as needed...
# Add to the existing server.py file

# Tools for Incidents
@mcp.tool()
async def create_incident(
    name: str,
    description: str,
    priority: str = "Medium",
    requester_email: Optional[str] = None,
    assignee_email: Optional[str] = None,
    site_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> str:
    """
    Create a new incident in SolarWinds Service Desk.
    
    Args:
        name: Title of the incident
        description: Detailed description of the incident
        priority: Priority level (Low, Medium, High, Critical)
        requester_email: Email of the user requesting the incident
        assignee_email: Email of the user to assign the incident to
        site_id: ID of the site associated with the incident
        department_id: ID of the department associated with the incident
    """
    data = {
        "incident": {
            "name": name,
            "description": description,
            "priority": priority,
        }
    }
    
    if requester_email:
        data["incident"]["requester"] = {"email": requester_email}
    
    if assignee_email:
        data["incident"]["assignee"] = {"email": assignee_email}
    
    if site_id:
        data["incident"]["site_id"] = site_id
    
    if department_id:
        data["incident"]["department_id"] = department_id
        
    response = await make_api_request("incidents.json", method="POST", data=data)
    return json.dumps(response, indent=2)

@mcp.tool()
async def update_incident(
    incident_id: Union[str, int],  # Accept both string and int
    name: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    state: Optional[str] = None,
    assignee_email: Optional[str] = None,
) -> str:
    """
    Update an existing incident with robust type conversion and error handling.
    
    Args:
        incident_id: ID of the incident to update
        name: New title of the incident
        description: New detailed description of the incident
        priority: Priority level (Low, Medium, High, Critical)
        state: State (New, Open, In Progress, Pending, Resolved, Closed)
        assignee_email: Email of the user to assign the incident to
    """
    # Ensure incident_id is a string
    incident_id_str = ensure_string_id(incident_id)
    
    # Prepare update payload
    data = {"incident": {}}
    
    if name:
        data["incident"]["name"] = name
    
    if description:
        data["incident"]["description"] = description
    
    # Apply fuzzy matching for priority to handle common misspellings
    if priority:
        valid_priorities = ["Low", "Medium", "High", "Critical"]
        corrected_priority = fuzzy_match_parameter(priority, valid_priorities)
        
        if corrected_priority:
            data["incident"]["priority"] = corrected_priority
            # If we corrected something, log it
            if corrected_priority.lower() != priority.lower():
                logger.info(f"Corrected priority value from '{priority}' to '{corrected_priority}'")
        else:
            data["incident"]["priority"] = priority
    
    # Apply fuzzy matching for state to handle common misspellings
    if state:
        valid_states = ["New", "Open", "In Progress", "Pending", "Resolved", "Closed"]
        corrected_state = fuzzy_match_parameter(state, valid_states)
        
        if corrected_state:
            data["incident"]["state"] = corrected_state
            # If we corrected something, log it
            if corrected_state.lower() != state.lower():
                logger.info(f"Corrected state value from '{state}' to '{corrected_state}'")
        else:
            data["incident"]["state"] = state
    
    if assignee_email:
        data["incident"]["assignee"] = {"email": assignee_email}
    
    try:
        response = await make_api_request(
            f"incidents/{incident_id_str}.json", 
            method="PUT", 
            data=data
        )
        return json.dumps(response, indent=2)
    except ValueError as e:
        error_msg = str(e)
        if "404" in error_msg:
            return json.dumps({
                "error": f"Incident with ID {incident_id} not found. Please verify the incident ID and try again.",
                "details": error_msg
            }, indent=2)
        return json.dumps({
            "error": "Incident update failed",
            "details": error_msg
        }, indent=2)

@mcp.tool()
async def add_comment_to_incident(
    incident_id: Union[str, int],  # Accept both string and int
    comment_body: str,
    is_private: bool = False,
) -> str:
    """
    Add a comment to an existing incident with robust type conversion.
    """
    # Ensure incident_id is a string
    incident_id_str = ensure_string_id(incident_id)
    
    data = {
        "comment": {
            "body": comment_body,
            "is_private": str(is_private).lower()
        }
    }
    
    try:
        response = await make_api_request(
            f"incidents/{incident_id_str}/comments.json", 
            method="POST", 
            data=data
        )
        return json.dumps(response, indent=2)
    except ValueError as e:
        return json.dumps({
            "error": "Comment creation failed",
            "details": str(e)
        }, indent=2)

# Tools for searching
@mcp.tool()
async def search_incidents(
    query: Optional[Union[str, int]] = None,
    updated_since: Optional[str] = None,
    state: Optional[str] = None,
    assignee_email: Optional[str] = None,
    requester_email: Optional[str] = None,
    priority: Optional[str] = None,
    department_id: Optional[Union[str, int]] = None,
    limit: Optional[int] = None,
    incident_id: Optional[Union[str, int]] = None,
) -> str:
    """
    Search for incidents with various filters and robust error handling.
    
    Args:
        query: Text to search for in the incident
        updated_since: Filter by update date (e.g., "7d" for 7 days)
        state: Filter by state (e.g., "New", "In Progress", "Resolved")
        assignee_email: Filter by assignee email
        requester_email: Filter by requester email
        priority: Filter by priority level (Low, Medium, High, Critical)
        department_id: Filter by department ID
        limit: Maximum number of incidents to return
        incident_id: Direct filter by incident ID
    """
    params = {}
    
    # Handle query parameter, which might be numeric
    if query is not None:
        params["query"] = str(query)
    
    # If incident_id is provided, search for specific incident
    if incident_id is not None:
        incident_id_str = ensure_string_id(incident_id)
        try:
            # Try direct fetch first
            try:
                response = await make_api_request(f"incidents/{incident_id_str}.json")
                return json.dumps([response], indent=2)  # Return as list for consistency
            except ValueError:
                # If direct fetch fails, try search
                params["query"] = str(incident_id)
        except Exception as e:
            logger.error(f"Error fetching incident by ID: {e}")
    
    # Standardize time period format
    if updated_since:
        # Handle various time formats users might enter
        if isinstance(updated_since, str) and updated_since.isdigit():
            # If just a number, assume days
            updated_since = f"{updated_since}d"
        
        # Remove any spaces if it's a string
        if isinstance(updated_since, str):
            updated_since = updated_since.replace(" ", "")
            
            # Ensure the format ends with d, w, or m
            if not any(updated_since.endswith(unit) for unit in ["d", "w", "m"]):
                updated_since = f"{updated_since}d"  # Default to days
                
        params["updated"] = str(updated_since)
    
    # Apply fuzzy matching for state
    if state:
        valid_states = ["New", "Open", "In Progress", "Pending", "Resolved", "Closed"]
        corrected_state = fuzzy_match_parameter(state, valid_states)
        
        if corrected_state:
            params["state"] = corrected_state
            # Log if we corrected something
            if corrected_state.lower() != state.lower():
                logger.info(f"Corrected state value from '{state}' to '{corrected_state}'")
        else:
            params["state"] = state
    
    # Apply fuzzy matching for priority
    if priority:
        valid_priorities = ["Low", "Medium", "High", "Critical"]
        corrected_priority = fuzzy_match_parameter(priority, valid_priorities)
        
        if corrected_priority:
            params["priority"] = corrected_priority
            # Log if we corrected something
            if corrected_priority.lower() != priority.lower():
                logger.info(f"Corrected priority value from '{priority}' to '{corrected_priority}'")
        else:
            params["priority"] = priority
    
    if assignee_email:
        params["assignee"] = assignee_email
    
    if requester_email:
        params["requester"] = requester_email
    
    if department_id:
        params["department"] = ensure_string_id(department_id)
    
    if limit and isinstance(limit, int) and limit > 0:
        params["per_page"] = str(min(limit, 100))  # API might have limits on max per_page
        
    try:
        response = await make_api_request("incidents.json", params=params)
        
        # Handle empty results
        if not response:
            return json.dumps({
                "message": "No incidents found matching your criteria", 
                "data": []
            }, indent=2)
            
        return json.dumps(response, indent=2)
    except ValueError as e:
        return json.dumps({
            "error": "Error searching for incidents",
            "details": str(e)
        }, indent=2)

# You can add more tools for other entities like problems, users, etc.

# Add to the existing server.py file

# Sites Resources
@mcp.resource("samanage://sites")
async def get_sites() -> str:
    """Get list of all sites."""
    response = await make_api_request("sites.json")
    return json.dumps(response, indent=2)

@mcp.resource("samanage://sites/{id}")
async def get_site(id: str) -> str:
    """Get detailed information about a specific site."""
    response = await make_api_request(f"sites/{id}.json")
    return json.dumps(response, indent=2)

# Departments Resources
@mcp.resource("samanage://departments")
async def get_departments() -> str:
    """Get list of all departments."""
    response = await make_api_request("departments.json")
    return json.dumps(response, indent=2)

@mcp.resource("samanage://departments/{id}")
async def get_department(id: str) -> str:
    """Get detailed information about a specific department."""
    response = await make_api_request(f"departments/{id}.json")
    return json.dumps(response, indent=2)

# Groups Resources
@mcp.resource("samanage://groups")
async def get_groups() -> str:
    """Get list of all groups."""
    response = await make_api_request("groups.json")
    return json.dumps(response, indent=2)

@mcp.resource("samanage://groups/{id}")
async def get_group(id: str) -> str:
    """Get detailed information about a specific group."""
    response = await make_api_request(f"groups/{id}.json")
    return json.dumps(response, indent=2)

# Tools for Problems
@mcp.tool()
async def create_problem(
    name: str,
    description: str,
    priority: str = "Medium",
    assignee_email: Optional[str] = None,
    requester_email: Optional[str] = None,  # Added requester_email parameter
    site_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> str:
    """
    Create a new problem in SolarWinds Service Desk.
    
    Args:
        name: Title of the problem
        description: Detailed description of the problem
        priority: Priority level (Low, Medium, High, Critical)
        assignee_email: Email of the user to assign the problem to
        requester_email: Email of the user requesting the problem
        site_id: ID of the site associated with the problem
        department_id: ID of the department associated with the problem
    """
    data = {
        "problem": {
            "name": name,
            "description": description,
            "priority": priority,
        }
    }
    
    if assignee_email:
        data["problem"]["assignee"] = {"email": assignee_email}
    
    # Add requester info - using the current user if not specified
    if requester_email:
        data["problem"]["requester"] = {"email": requester_email}
    else:
        # Fallback to the account's default user if available
        try:
            current_user = await make_api_request("current_user.json")
            if current_user and "email" in current_user:
                data["problem"]["requester"] = {"email": current_user["email"]}
        except Exception:
            pass
    
    if site_id:
        data["problem"]["site_id"] = site_id
    
    if department_id:
        data["problem"]["department_id"] = department_id
        
    try:
        response = await make_api_request("problems.json", method="POST", data=data)
        return json.dumps(response, indent=2)
    except ValueError as e:
        if "requester" in str(e):
            return "Error: A valid requester email is required. Please provide a requester_email parameter."
        return f"Error creating problem: {str(e)}"
    
@mcp.tool()
async def search_for_related_incidents(
    query: str,
    limit: int = 5
) -> str:
    """
    Search for incidents related to a specific issue.
    
    Args:
        query: Search term to find related incidents
        limit: Maximum number of incidents to return
    """
    params = {
        "query": query,
        "per_page": str(limit)
    }
    
    response = await make_api_request("incidents.json", params=params)
    return json.dumps(response, indent=2)
# Prompt for incident analysis
@mcp.prompt()
def analyze_incident(incident_id: str) -> str:
    """
    Generate a prompt for analyzing a specific incident.
    
    Args:
        incident_id: ID of the incident to analyze
    """
    return f"""
    Please analyze the following ServiceDesk incident:
    
    incident_id: {incident_id}
    
    First, I'll need to get the incident details. I'll use the resource at samanage://incidents/{incident_id}.
    
    1. Summarize the key details of the incident.
    2. Analyze the priority and urgency.
    3. Review any comments or updates.
    4. Suggest next steps for resolution.
    5. Recommend if the priority or assignment should be changed.
    """

# Prompt for creating incident report
@mcp.prompt()
def create_incident_report(days: str = "7") -> str:
    """
    Generate a prompt for creating an incident report.
    
    Args:
        days: Number of days to include in the report
    """
    return f"""
    Please create a comprehensive incident report for the past {days} days.
    
    I'll need to retrieve recent incidents. I'll use the search_incidents tool with updated_since="{days}d".
    
    Once I have the data, please:
    
    1. Summarize the total number of incidents created and resolved.
    2. Break down incidents by priority and status.
    3. Identify any trends or recurring issues.
    4. Highlight incidents that have been open for an extended period.
    5. Recommend areas for improvement in incident management.
    """

# Prompt for user support analysis
@mcp.prompt()
def analyze_user_support(user_email: str) -> str:
    """
    Generate a prompt for analyzing support history for a specific user.
    
    Args:
        user_email: Email of the user to analyze
    """
    return f"""
    Please analyze the support history for user with email {user_email}.
    
    I'll search for incidents related to this user using the search_incidents tool with requester_email="{user_email}".
    
    Please provide:
    
    1. A summary of the user's support history.
    2. Analysis of the types of issues reported.
    3. Identify any recurring problems.
    4. Suggestions for how to improve support for this user.
    5. Recommendations for proactive measures to reduce future incidents.
    """
# Tools for Solutions

@mcp.tool()
async def search_solutions(
    query: Optional[str] = None,
    state: Optional[str] = None, 
    category_id: Optional[int] = None,
    updated_since: Optional[str] = None,
    creator_id: Optional[int] = None,
    limit: int = 10
) -> str:
    """
    Enhanced solution search with robust type handling and error management.
    """
    params = {}
    
    if query:
        params["query"] = query
    
    if state:
        params["state"] = state
    
    if category_id is not None:
        params["category_id"] = ensure_string_id(category_id)
    
    if updated_since:
        params["updated"] = updated_since
        
    if creator_id is not None:
        params["creator_id"] = ensure_string_id(creator_id)
    
    params["per_page"] = str(limit)
        
    try:
        response = await make_api_request("solutions.json", params=params)
        return json.dumps(response, indent=2)
    except ValueError as e:
        return json.dumps({
            "error": "Solution search failed",
            "details": str(e)
        }, indent=2)

@mcp.tool()
async def vote_on_solution(
    solution_id: Union[str, int],  # Accept both string and int
    vote: bool  # True for upvote, False for downvote
) -> str:
    """
    Vote on a solution's helpfulness.
    
    Args:
        solution_id: ID of the solution
        vote: True for upvote, False for downvote
    """
    vote_type = "up" if vote else "down"
    
    try:
        # Ensure solution_id is a string
        solution_id_str = ensure_string_id(solution_id)
            
        response = await make_api_request(
            f"solutions/{solution_id_str}/votes/{vote_type}.json", 
            method="POST",
            data={}
        )
        return json.dumps(response, indent=2)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return f"Error: Solution with ID {solution_id} not found. Please verify the solution ID exists and try again."
        return f"Error voting on solution: {error_msg}"
# Resources for Solutions

@mcp.resource("samanage://solutions/search/{query}")
async def solutions_search_resource(query: str) -> str:
    """Search solutions matching the query text."""
    response = await make_api_request("solutions.json", params={"query": query})
    return json.dumps(response, indent=2)

@mcp.resource("samanage://solutions/by-state/{state}")
async def solutions_by_state_resource(state: str) -> str:
    """Get solutions filtered by state."""
    response = await make_api_request("solutions.json", params={"state": state})
    return json.dumps(response, indent=2)

@mcp.resource("samanage://solutions/by-category/{category_id}")
async def solutions_by_category_resource(category_id: str) -> str:
    """Get solutions filtered by category ID."""
    response = await make_api_request("solutions.json", params={"category_id": category_id})
    return json.dumps(response, indent=2)

# Prompts for Solutions

@mcp.prompt()
def analyze_solution_usage(solution_id: str) -> str:
    """
    Generate a prompt for analyzing solution usage.
    
    Args:
        solution_id: ID of the solution to analyze
    """
    return f"""
    Please analyze the following knowledge base solution:
    
    solution_id: {solution_id}
    
    First, I'll need to get the solution details. I'll use the resource at samanage://solutions/{solution_id}.
    
    1. Summarize the key details of the solution.
    2. Check for solution votes and popularity.
    3. Identify related incidents that referenced this solution.
    4. Suggest improvements to the solution content.
    5. Recommend categories or tags that might make this solution more discoverable.
    """

@mcp.prompt()
def create_solution_draft(
    title: str, 
    problem: str,
    resolution: str,
    state: str = "Draft"
) -> str:
    """
    Generate a prompt for creating a new solution draft.
    
    Args:
        title: Title for the new solution
        problem: Description of the problem the solution addresses
        resolution: Steps to resolve the problem
        state: Initial state (e.g., "Draft", "Approved")
    """
    return f"""
    Please help me create a well-formatted knowledge base solution with the following information:
    
    Title: {title}
    Problem: {problem}
    Resolution: {resolution}
    Initial State: {state}
    
    1. Format this information into a clear, structured solution article.
    2. Add appropriate HTML formatting for readability (like <h2>, <ul>, <code> tags).
    3. Suggest appropriate categories and tags.
    4. Structure the final JSON payload I can use with the create_solution tool.
    
    This solution will be used by our support team to help customers resolve common issues.
    """

# Tools for Roles


@mcp.tool()
async def search_users_by_role(
    role_id: Optional[str] = None,
    role_name: Optional[str] = None,
    limit: int = 20
) -> str:
    """
    Search for users with a specific role.
    
    Args:
        role_id: ID of the role to filter by
        role_name: Name of the role to filter by (used if role_id not provided)
        limit: Maximum number of users to return
    """
    params = {"per_page": str(limit)}
    
    # First get all users
    users_response = await make_api_request("users.json", params=params)
    
    # If no role filter, return all users
    if not role_id and not role_name:
        return json.dumps(users_response, indent=2)
        
    # If we have a role name but not ID, try to find the role ID
    if role_name and not role_id:
        roles_response = await make_api_request("roles.json")
        for role in roles_response:
            if role.get("name", "").lower() == role_name.lower():
                role_id = role.get("id")
                break
        
        if not role_id:
            return json.dumps({"error": f"Role with name '{role_name}' not found"}, indent=2)
    
    # Filter users by role
    filtered_users = []
    for user in users_response:
        if user.get("role", {}).get("id") == role_id:
            filtered_users.append(user)
    
    return json.dumps(filtered_users, indent=2)

# Resources for Roles

@mcp.resource("samanage://users/by-role/{role_id}")
async def users_by_role_resource(role_id: str) -> str:
    """Get users with a specific role."""
    # Get all users
    users_response = await make_api_request("users.json")
    
    # Filter users by role
    filtered_users = [user for user in users_response if user.get("role", {}).get("id") == role_id]
    
    return json.dumps(filtered_users, indent=2)

@mcp.resource("samanage://roles/permissions")
async def role_permissions_resource() -> str:
    """
    Get available role permissions information.
    
    Note: This is a simulated resource as the API may not directly expose 
    a permissions endpoint. This provides helpful context about common 
    SolarWinds Service Desk role permissions.
    """
    permissions = {
        "available_permissions": [
            {"name": "view_incidents", "description": "View incidents"},
            {"name": "create_incidents", "description": "Create incidents"},
            {"name": "update_incidents", "description": "Update incidents"},
            {"name": "view_problems", "description": "View problems"},
            {"name": "create_problems", "description": "Create problems"},
            {"name": "view_changes", "description": "View changes"},
            {"name": "approve_changes", "description": "Approve changes"},
            {"name": "admin_portal", "description": "Access admin portal"},
            {"name": "view_reports", "description": "View reports"},
            {"name": "manage_users", "description": "Manage users"}
        ],
        "common_roles": [
            {
                "name": "Admin",
                "description": "Full system access",
                "typical_permissions": ["admin_portal", "manage_users", "all_entity_permissions"]
            },
            {
                "name": "Help Desk",
                "description": "Support staff role",
                "typical_permissions": ["view_incidents", "create_incidents", "update_incidents"]
            },
            {
                "name": "Self Service",
                "description": "Limited end-user access",
                "typical_permissions": ["view_own_incidents", "create_incidents"]
            }
        ]
    }
    return json.dumps(permissions, indent=2)


# Prompts for Roles

@mcp.prompt()
def role_audit(days: str = "30") -> str:
    """
    Generate a prompt for auditing role assignments.
    
    Args:
        days: Number of days of user activity to analyze
    """
    return f"""
    Please perform a comprehensive role audit for the past {days} days.
    
    I'll need to retrieve:
    1. All roles using the resource at samanage://roles
    2. All users using the resource at samanage://users
    3. Common role permissions information using samanage://roles/permissions
    
    Once I have this data, please:
    
    1. Summarize the current role distribution across users.
    2. Identify users with administrative privileges.
    3. Check for unusual role assignments (e.g., too many admins).
    4. Recommend role optimization opportunities.
    5. Suggest potential security improvements in role assignments.
    
    This audit will help us ensure proper access control and security in our service desk.
    """

@mcp.prompt()
def create_role_template(
    name: str, 
    description: str, 
    portal_access: bool = True,
    show_my_tasks: bool = False
) -> str:
    """
    Generate a prompt for creating a new role.
    
    Args:
        name: Name for the new role
        description: Description of the role's purpose
        portal_access: Whether the role should have portal access
        show_my_tasks: Whether to show the user's tasks
    """
    return f"""
    Please help me create a new role with the following parameters:
    
    Name: {name}
    Description: {description}
    Portal Access: {"Yes" if portal_access else "No"}
    Show My Tasks: {"Yes" if show_my_tasks else "No"}
    
    First, I'll check existing roles using the resource at samanage://roles.
    
    Then, please help me:
    
    1. Define appropriate permissions for this role based on its name and description.
    2. Structure a JSON payload I can use with the create_role tool.
    3. Suggest which types of users should be assigned this role.
    4. Recommend any additional settings or restrictions for this role type.
    
    After creating the role, I'll need to assign it to relevant users.
    """


# Tools for Departments

@mcp.tool()
async def assign_users_to_department(
    department_id: str,
    user_ids: list[str]
) -> str:
    """
    Assign multiple users to a department.
    
    Args:
        department_id: ID of the department
        user_ids: List of user IDs to assign to the department
    """
    results = []
    errors = []
    
    for user_id in user_ids:
        try:
            data = {
                "user": {
                    "department": {
                        "id": department_id
                    }
                }
            }
            
            response = await make_api_request(f"users/{user_id}.json", method="PUT", data=data)
            results.append({"user_id": user_id, "status": "success", "response": response})
        except Exception as e:
            errors.append({"user_id": user_id, "error": str(e)})
    
    return json.dumps({
        "successful_assignments": len(results),
        "failed_assignments": len(errors),
        "results": results,
        "errors": errors
    }, indent=2)

@mcp.tool()
async def analyze_department_metrics(
    department_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Analyze incident metrics for departments.
    
    Args:
        department_id: Optional ID of specific department to analyze (all if not specified)
        start_date: Starting date for analysis (format: 'YYYY-MM-DD')
        end_date: Ending date for analysis (format: 'YYYY-MM-DD')
    """
    # Build date filter params
    params = {}
    if start_date:
        params["created_from"] = start_date
    if end_date:
        params["created_to"] = end_date
    
    # Get incidents
    incidents_response = await make_api_request("incidents.json", params=params)
    
    # Get departments (for names)
    departments_response = await make_api_request("departments.json")
    dept_name_map = {d["id"]: d["name"] for d in departments_response if "id" in d and "name" in d}
    
    # Filter and group incidents by department
    dept_metrics = {}
    for incident in incidents_response:
        dept_id = incident.get("department", {}).get("id")
        if dept_id is None:
            continue
        
        # Skip if we're looking for a specific department and this isn't it
        if department_id and dept_id != department_id:
            continue
            
        # Init department entry if not exists
        if dept_id not in dept_metrics:
            dept_metrics[dept_id] = {
                "department_id": dept_id,
                "department_name": dept_name_map.get(dept_id, "Unknown"),
                "total_incidents": 0,
                "open_incidents": 0,
                "resolved_incidents": 0,
                "high_priority_incidents": 0,
                "avg_resolution_time_days": 0,
                "resolution_times": []
            }
        
        # Update metrics
        dept_metrics[dept_id]["total_incidents"] += 1
        
        # Count by state
        if incident.get("state") in ["Resolved", "Closed"]:
            dept_metrics[dept_id]["resolved_incidents"] += 1
            
            # Calculate resolution time if available
            created = incident.get("created_at")
            resolved = incident.get("resolved_at")
            if created and resolved:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    resolved_dt = datetime.fromisoformat(resolved.replace('Z', '+00:00'))
                    resolution_time_days = (resolved_dt - created_dt).total_seconds() / 86400
                    dept_metrics[dept_id]["resolution_times"].append(resolution_time_days)
                except Exception:
                    pass
        else:
            dept_metrics[dept_id]["open_incidents"] += 1
        
        # Count by priority
        if incident.get("priority") in ["High", "Critical"]:
            dept_metrics[dept_id]["high_priority_incidents"] += 1
    
    # Calculate averages
    for dept_id, metrics in dept_metrics.items():
        resolution_times = metrics.pop("resolution_times", [])
        if resolution_times:
            metrics["avg_resolution_time_days"] = sum(resolution_times) / len(resolution_times)
    
    # Convert to list for output
    metrics_list = list(dept_metrics.values())
    
    # Sort by total incidents
    metrics_list.sort(key=lambda x: x["total_incidents"], reverse=True)
    
    return json.dumps(metrics_list, indent=2)
def ensure_string_id(id_value: Union[str, int, None]) -> Optional[str]:
    """
    Converts various ID types to a consistent string format.
    
    Args:
        id_value: ID in various possible formats
    
    Returns:
        Standardized string ID or None
    """
    if id_value is None:
        return None
    
    # Convert to string
    id_str = str(id_value)
    
    # Remove any domain or additional parts
    if '-' in id_str:
        id_str = id_str.split('-')[0]
    
    return id_str

def fuzzy_match_parameter(input_value: str, valid_values: List[str], threshold: float = 0.7) -> Optional[str]:
    """
    Find the closest match for an input value in a list of valid values.
    
    Args:
        input_value: The input string to match
        valid_values: List of valid string values to match against
        threshold: Minimum similarity score (0-1) to consider a match
        
    Returns:
        The closest matching valid value, or None if no match meets the threshold
    """
    if not input_value or not valid_values:
        return None
        
    # For case-insensitive matching
    input_lower = input_value.lower()
    valid_lower = [v.lower() for v in valid_values]
    
    # Check for exact matches first
    if input_lower in valid_lower:
        index = valid_lower.index(input_lower)
        return valid_values[index]
    
    # Use difflib for fuzzy matching
    from difflib import get_close_matches
    matches = get_close_matches(input_lower, valid_lower, n=1, cutoff=threshold)
    
    if matches:
        index = valid_lower.index(matches[0])
        return valid_values[index]
    
    return None

# Resources for Departments

@mcp.resource("samanage://departments/stats")
async def department_stats_resource() -> str:
    """Get statistics about departments and their incident volumes."""
    # Get all departments
    departments = await make_api_request("departments.json")
    
    # Get incident counts by department
    incident_stats = {}
    for dept in departments:
        dept_id = dept.get("id")
        if dept_id:
            incidents = await make_api_request("incidents.json", params={"department": dept_id})
            incident_stats[dept_id] = {
                "id": dept_id,
                "name": dept.get("name", "Unknown"),
                "incident_count": len(incidents),
                "description": dept.get("description", "")
            }
    
    return json.dumps(incident_stats, indent=2)

@mcp.resource("samanage://departments/{department_id}/users")
async def department_users_resource(department_id: str) -> str:
    """Get users assigned to a specific department."""
    users = await make_api_request("users.json")
    
    # Filter users by department
    department_users = [
        user for user in users 
        if user.get("department", {}).get("id") == department_id
    ]
    
    return json.dumps(department_users, indent=2)

# Prompts for Departments

@mcp.prompt()
def department_incident_analysis(
    department_id: str, 
    period: str = "30"
) -> str:
    """
    Generate a prompt for analyzing department incidents.
    
    Args:
        department_id: ID of the department to analyze
        period: Number of days for the analysis period
    """
    return f"""
    Please analyze incidents for department ID {department_id} over the past {period} days.
    
    I'll need:
    1. Department details using the resource at samanage://departments/{department_id}
    2. Department users using the resource at samanage://departments/{department_id}/users
    3. Recent incidents using search_incidents with department_id={department_id} and updated_since="{period}d"
    
    Once I have this data, please:
    
    1. Summarize the department's key information and staffing.
    2. Analyze incident volume trends over time.
    3. Evaluate response times compared to SLAs.
    4. Identify common incident categories and priorities.
    5. Recommend resource allocation or process improvements.
    6. Highlight any concerning patterns or areas for improvement.
    
    The analysis will help understand this department's support efficiency and workload.
    """

@mcp.prompt()
def department_workload_distribution() -> str:
    """
    Generate a prompt for analyzing workload distribution across departments.
    """
    return f"""
    Please analyze the workload distribution across all departments.
    
    I'll need:
    1. All departments using the resource at samanage://departments
    2. Department statistics using the resource at samanage://departments/stats
    3. Open incident counts per department by querying search_incidents with state="Open" for each department
    
    Once I have this data, please:
    
    1. Summarize incident distribution across departments.
    2. Identify departments with unusually high or low workloads.
    3. Calculate the ratio of open incidents to department size (if user data available).
    4. Recommend workload balancing approaches.
    5. Suggest optimal department structures based on current support patterns.
    
    This analysis will help ensure fair workload distribution and appropriate staffing.
    """

# Tools for Categories

@mcp.tool()
async def analyze_category_distribution(
    parent_category_id: Optional[str] = None,
    time_period: str = "30d"
) -> str:
    """
    Analyze incident distribution across categories.
    
    Args:
        parent_category_id: Optional parent category ID to filter subcategories
        time_period: Time period for analysis (e.g., "7d", "30d", "90d")
    """
    # Get categories
    categories_response = await make_api_request("categories.json")
    
    # Filter by parent if specified
    if parent_category_id:
        categories = [c for c in categories_response if c.get("parent_id") == parent_category_id]
    else:
        categories = categories_response
    
    # Get incidents within time period
    incidents_response = await make_api_request("incidents.json", params={"updated": time_period})
    
    # Count incidents per category
    category_counts = {}
    for incident in incidents_response:
        # Get category ID
        category_id = incident.get("category", {}).get("id")
        if not category_id:
            continue
            
        if category_id not in category_counts:
            category_counts[category_id] = {
                "count": 0,
                "high_priority": 0,
                "resolved": 0,
                "open": 0
            }
            
        category_counts[category_id]["count"] += 1
        
        # Count by priority
        if incident.get("priority") in ["High", "Critical"]:
            category_counts[category_id]["high_priority"] += 1
            
        # Count by state
        if incident.get("state") in ["Resolved", "Closed"]:
            category_counts[category_id]["resolved"] += 1
        else:
            category_counts[category_id]["open"] += 1
    
    # Build result with category details and counts
    results = []
    for category in categories:
        category_id = category.get("id")
        if category_id:
            category_data = {
                "id": category_id,
                "name": category.get("name", "Unknown"),
                "parent_id": category.get("parent_id"),
                "incident_count": 0,
                "high_priority_count": 0,
                "open_count": 0,
                "resolved_count": 0
            }
            
            # Add count data if we have it
            if category_id in category_counts:
                counts = category_counts[category_id]
                category_data.update({
                    "incident_count": counts["count"],
                    "high_priority_count": counts["high_priority"],
                    "open_count": counts["open"],
                    "resolved_count": counts["resolved"]
                })
                
            results.append(category_data)
    
    # Sort by incident count
    results.sort(key=lambda x: x["incident_count"], reverse=True)
    
    return json.dumps(results, indent=2)

@mcp.tool()
async def manage_subcategories(
    parent_category_id: str,
    operation: str,
    subcategory_data: Optional[dict] = None,
    subcategory_id: Optional[str] = None
) -> str:
    """
    Manage subcategories for a parent category.
    
    Args:
        parent_category_id: ID of the parent category
        operation: One of: "list", "create", "update", "delete"
        subcategory_data: Data for create/update operations (containing name, description, etc.)
        subcategory_id: ID of subcategory for update/delete operations
    """
    if operation.lower() == "list":
        # Get all categories
        categories = await make_api_request("categories.json")
        
        # Filter by parent ID
        subcategories = [c for c in categories if c.get("parent_id") == parent_category_id]
        
        return json.dumps(subcategories, indent=2)
        
    elif operation.lower() == "create":
        if not subcategory_data:
            return json.dumps({"error": "subcategory_data is required for create operation"}, indent=2)
            
        # Ensure parent_id is set
        if "category" not in subcategory_data:
            subcategory_data["category"] = {}
        
        subcategory_data["category"]["parent_id"] = parent_category_id
        
        # Create subcategory
        response = await make_api_request("categories.json", method="POST", data=subcategory_data)
        return json.dumps(response, indent=2)
        
    elif operation.lower() == "update":
        if not subcategory_id:
            return json.dumps({"error": "subcategory_id is required for update operation"}, indent=2)
            
        if not subcategory_data:
            return json.dumps({"error": "subcategory_data is required for update operation"}, indent=2)
        
        # Update subcategory
        response = await make_api_request(f"categories/{subcategory_id}.json", method="PUT", data=subcategory_data)
        return json.dumps(response, indent=2)
        
    elif operation.lower() == "delete":
        if not subcategory_id:
            return json.dumps({"error": "subcategory_id is required for delete operation"}, indent=2)
            
        # Delete subcategory
        response = await make_api_request(f"categories/{subcategory_id}.json", method="DELETE")
        return json.dumps(response, indent=2)
        
    else:
        return json.dumps({"error": f"Unknown operation: {operation}"}, indent=2)
    
# Resources for Categories

@mcp.resource("samanage://categories/hierarchy")
async def category_hierarchy_resource() -> str:
    """Get the complete category hierarchy structure."""
    # Get all categories
    categories = await make_api_request("categories.json")
    
    # Build hierarchy map (parent_id -> list of children)
    hierarchy = {}
    root_categories = []
    
    # First pass: group by parent
    for category in categories:
        cat_id = category.get("id")
        parent_id = category.get("parent_id")
        
        if not parent_id or parent_id == "null":
            # This is a root category
            root_categories.append(category)
        else:
            # Add to parent's children
            if parent_id not in hierarchy:
                hierarchy[parent_id] = []
            hierarchy[parent_id].append(category)
    
    # Function to build tree recursively
    def build_tree(category):
        cat_id = category.get("id")
        category_tree = {
            "id": cat_id,
            "name": category.get("name", "Unknown"),
            "children": []
        }
        
        # Add children if any
        if cat_id in hierarchy:
            category_tree["children"] = [build_tree(child) for child in hierarchy[cat_id]]
            
        return category_tree
    
    # Build complete tree
    result = [build_tree(root) for root in root_categories]
    
    return json.dumps(result, indent=2)

@mcp.resource("samanage://categories/popularity")
async def category_popularity_resource() -> str:
    """Get categories ranked by incident volume."""
    # Get all categories
    categories = await make_api_request("categories.json")
    
    # Get incidents
    incidents = await make_api_request("incidents.json")
    
    # Count incidents per category
    category_counts = {}
    for incident in incidents:
        category = incident.get("category", {})
        cat_id = category.get("id")
        if not cat_id:
            continue
            
        if cat_id not in category_counts:
            category_counts[cat_id] = 0
        
        category_counts[cat_id] += 1
    
    # Build result
    results = []
    for category in categories:
        cat_id = category.get("id")
        if cat_id:
            results.append({
                "id": cat_id,
                "name": category.get("name", "Unknown"),
                "incident_count": category_counts.get(cat_id, 0),
                "parent_id": category.get("parent_id")
            })
    
    # Sort by incident count
    results.sort(key=lambda x: x["incident_count"], reverse=True)
    
    return json.dumps(results, indent=2)

# Prompts for Categories

@mcp.prompt()
def suggest_category_improvements() -> str:
    """
    Generate a prompt for analyzing and improving category structure.
    """
    return f"""
    Please analyze our category structure and suggest improvements.
    
    I'll need:
    1. The current category hierarchy using the resource at samanage://categories/hierarchy
    2. Category popularity data using the resource at samanage://categories/popularity
    3. Sample incidents for uncategorized or miscategorized tickets
    
    Once I have this data, please:
    
    1. Identify unused or rarely used categories.
    2. Detect overloaded categories that might benefit from being split.
    3. Suggest new subcategories for high-volume parent categories.
    4. Identify potential category naming improvements.
    5. Recommend an optimized category structure.
    
    This analysis will help us ensure our incident categorization is effective and makes reporting more valuable.
    """

@mcp.prompt()
def category_incident_allocation(category_id: str) -> str:
    """
    Generate a prompt for analyzing incidents in a specific category.
    
    Args:
        category_id: ID of the category to analyze
    """
    return f"""
    Please analyze the incidents assigned to category ID {category_id}.
    
    I'll need:
    1. Category details using the resource at samanage://categories/{category_id}
    2. Incidents in this category using search_incidents with "category_id={category_id}"
    3. Subcategories using manage_subcategories with parent_category_id={category_id} and operation="list"
    
    Once I have this data, please:
    
    1. Summarize the category purpose and current volumes.
    2. Identify common themes among incidents in this category.
    3. Analyze if subcategories are being used effectively.
    4. Detect patterns that might indicate miscategorized incidents.
    5. Recommend optimization strategies (e.g., new subcategories, renaming, merging).
    
    This analysis will help us improve our incident categorization for better reporting and trend analysis.
    """

# Tools for Tasks

@mcp.tool()
async def search_tasks(
    object_type: str,
    object_id: str,
    assignee_id: Optional[str] = None,
    is_complete: Optional[bool] = None,
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    priority: Optional[str] = None
) -> str:
    """
    Search for tasks with various filters.
    
    Args:
        object_type: Parent object type (e.g., "incidents", "problems", "changes")
        object_id: ID of the parent object
        assignee_id: Filter by assignee user ID
        is_complete: Filter by completion status (True/False)
        due_date_from: Filter by due date (format: YYYY-MM-DD)
        due_date_to: Filter by due date (format: YYYY-MM-DD)
        priority: Filter by priority level
    """
    # Get all tasks for the object
    tasks_response = await make_api_request(f"{object_type}/{object_id}/tasks.json")
    
    # Filter tasks based on criteria
    filtered_tasks = []
    for task in tasks_response:
        # Check assignee filter
        if assignee_id is not None:
            task_assignee_id = task.get("assignee", {}).get("id")
            if str(task_assignee_id) != str(assignee_id):
                continue
        
        # Check completion status filter
        if is_complete is not None:
            task_complete = task.get("is_complete", False)
            if task_complete != is_complete:
                continue
        
        # Check due date from filter
        if due_date_from is not None:
            task_due_date = task.get("due_at")
            if not task_due_date or task_due_date < due_date_from:
                continue
        
        # Check due date to filter
        if due_date_to is not None:
            task_due_date = task.get("due_at")
            if not task_due_date or task_due_date > due_date_to:
                continue
        
        # Check priority filter
        if priority is not None:
            task_priority = task.get("priority")
            if task_priority != priority:
                continue
        
        # Task passed all filters
        filtered_tasks.append(task)
    
    return json.dumps(filtered_tasks, indent=2)

@mcp.tool()
async def batch_create_tasks(
    object_type: str,
    object_id: Union[str, int],
    tasks: List[Dict[str, Any]]
) -> str:
    """
    Create multiple tasks with robust type conversion and error handling.
    """
    # Convert object ID to string
    object_id_str = ensure_string_id(object_id)
    
    results = []
    errors = []
    
    for task_data in tasks:
        # Convert any ID fields in the task
        converted_task = {
            k: ensure_string_id(v) if k.endswith('_id') else v 
            for k, v in task_data.items()
        }
        
        try:
            response = await make_api_request(
                f"{object_type}/{object_id_str}/tasks.json",
                method="POST",
                data={"task": converted_task}
            )
            results.append({
                "status": "success",
                "task": response
            })
        except Exception as e:
            errors.append({
                "status": "error",
                "task_data": converted_task,
                "error": str(e)
            })
    
    return json.dumps({
        "successful_creations": len(results),
        "failed_creations": len(errors),
        "results": results,
        "errors": errors
    }, indent=2)

@mcp.tool()
async def analyze_task_completion(
    object_type: str,
    object_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    date_range: Optional[str] = "30d"
) -> str:
    """
    Analyze task completion statistics.
    
    Args:
        object_type: Object type to analyze tasks for (e.g., "incidents", "problems")
        object_id: Optional specific object ID (if None, analyzes across all objects)
        assignee_id: Optional assignee to filter by
        date_range: Time period for analysis (e.g., "7d", "30d", "90d")
    """
    # Initialize tasks_response as an empty list
    tasks_response = []
    
    # If object_id is provided, get tasks for that specific object
    if object_id:
        try:
            tasks_response = await make_api_request(f"{object_type}/{object_id}/tasks.json")
        except Exception as e:
            return f"Error retrieving tasks: {str(e)}"
    else:
        # For analyzing across all objects, we need a different approach
        # Note: The SolarWinds API might not directly support querying all tasks
        # This is a simplified approximation
        
        # First get objects of the specified type
        try:
            objects_response = await make_api_request(f"{object_type}.json", 
                                                   params={"updated": date_range})
            
            # Collect tasks from each object
            all_tasks = []
            for obj in objects_response[:20]:  # Limit to avoid too many API calls
                obj_id = obj.get("id")
                if obj_id:
                    try:
                        obj_tasks = await make_api_request(f"{object_type}/{obj_id}/tasks.json")
                        all_tasks.extend(obj_tasks)
                    except Exception:
                        # Continue even if we can't get tasks for a specific object
                        continue
            
            # Set tasks_response to the collected tasks
            tasks_response = all_tasks
        except Exception as e:
            return f"Error retrieving objects: {str(e)}"
    
    # Filter by assignee if specified
    if assignee_id:
        tasks_response = [
            task for task in tasks_response 
            if task.get("assignee", {}).get("id") == assignee_id
        ]
    
    # Check if we have any tasks to analyze
    if not tasks_response:
        return json.dumps({
            "summary": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "completion_rate": 0,
                "total_assignees": 0
            },
            "assignee_statistics": []
        }, indent=2)
    
    # Calculate statistics
    total_tasks = len(tasks_response)
    completed_tasks = sum(1 for task in tasks_response if task.get("is_complete", False))
    completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    
    # Group tasks by assignee
    assignee_stats = {}
    for task in tasks_response:
        assignee = task.get("assignee", {})
        assignee_id = assignee.get("id")
        assignee_name = assignee.get("name", "Unassigned")
        
        if assignee_id not in assignee_stats:
            assignee_stats[assignee_id] = {
                "assignee_id": assignee_id,
                "assignee_name": assignee_name,
                "total_tasks": 0,
                "completed_tasks": 0,
                "completion_rate": 0,
                "overdue_tasks": 0
            }
        
        # Update stats
        assignee_stats[assignee_id]["total_tasks"] += 1
        
        if task.get("is_complete", False):
            assignee_stats[assignee_id]["completed_tasks"] += 1
        
        # Check if overdue
        due_at = task.get("due_at")
        is_complete = task.get("is_complete", False)
        
        if due_at and not is_complete:
            try:
                due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                if due_date < datetime.now(timezone.utc):
                    assignee_stats[assignee_id]["overdue_tasks"] += 1
            except (ValueError, AttributeError):
                # Skip if date parsing fails
                pass
    
    # Calculate completion rates
    for stats in assignee_stats.values():
        if stats["total_tasks"] > 0:
            stats["completion_rate"] = (stats["completed_tasks"] / stats["total_tasks"]) * 100
    
    # Convert to list and sort by total tasks
    assignee_stats_list = list(assignee_stats.values())
    assignee_stats_list.sort(key=lambda x: x["total_tasks"], reverse=True)
    
    result = {
        "summary": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": completion_rate,
            "total_assignees": len(assignee_stats)
        },
        "assignee_statistics": assignee_stats_list
    }
    
    return json.dumps(result, indent=2)
# Resources for Tasks

@mcp.resource("samanage://tasks/overdue")
async def overdue_tasks_resource() -> str:
    """Get all overdue tasks across the system."""
    # Get main object types
    object_types = ["incidents", "problems", "changes"]
    
    overdue_tasks = []
    for obj_type in object_types:
        # Get objects of this type
        objects = await make_api_request(f"{obj_type}.json")
        
        # Get tasks for each object (limit to reduce API calls)
        for obj in objects[:20]:
            obj_id = obj.get("id")
            if not obj_id:
                continue
                
            tasks = await make_api_request(f"{obj_type}/{obj_id}/tasks.json")
            
            # Check for overdue tasks
            for task in tasks:
                due_at = task.get("due_at")
                is_complete = task.get("is_complete", False)
                
                if due_at and not is_complete:
                    try:
                        due_date = datetime.fromisoformat(due_at.replace('Z', '+00:00'))
                        if due_date < datetime.now(timezone.utc):
                            # Add object reference
                            task["_object_type"] = obj_type
                            task["_object_id"] = obj_id
                            task["_object_name"] = obj.get("name", "Unknown")
                            
                            overdue_tasks.append(task)
                    except (ValueError, TypeError):
                        # Skip if date parsing fails
                        pass
    
    return json.dumps(overdue_tasks, indent=2)

@mcp.resource("samanage://tasks/by-assignee/{assignee_id}")
async def tasks_by_assignee_resource(assignee_id: str) -> str:
    """Get all tasks assigned to a specific user."""
    # Get main object types
    object_types = ["incidents", "problems", "changes"]
    
    assigned_tasks = []
    for obj_type in object_types:
        # Get objects of this type
        objects = await make_api_request(f"{obj_type}.json")
        
        # Get tasks for each object (limit to reduce API calls)
        for obj in objects[:20]:
            obj_id = obj.get("id")
            if not obj_id:
                continue
                
            tasks = await make_api_request(f"{obj_type}/{obj_id}/tasks.json")
            
            # Filter by assignee
            for task in tasks:
                task_assignee_id = task.get("assignee", {}).get("id")
                if str(task_assignee_id) == str(assignee_id):
                    # Add object reference
                    task["_object_type"] = obj_type
                    task["_object_id"] = obj_id
                    task["_object_name"] = obj.get("name", "Unknown")
                    
                    assigned_tasks.append(task)
    
    return json.dumps(assigned_tasks, indent=2)

# Prompts for Tasks

@mcp.prompt()
def task_workload_analysis(user_id: Optional[str] = None) -> str:
    """
    Generate a prompt for analyzing task workload.
    
    Args:
        user_id: Optional user ID to focus analysis on
    """
    user_focus = f"for user ID {user_id}" if user_id else "across all users"
    
    return f"""
    Please analyze the task workload distribution {user_focus}.
    
    I'll need to gather:
    1. {"Tasks assigned to this user using the resource at samanage://tasks/by-assignee/{user_id}" if user_id else "Overdue tasks using the resource at samanage://tasks/overdue"}
    2. Task completion statistics using the analyze_task_completion tool
    
    Once I have this data, please:
    
    1. Summarize the current task workload {user_focus}.
    2. Identify overdue or at-risk tasks.
    3. Analyze completion rates and efficiency patterns.
    4. Recommend task prioritization and workload balancing.
    5. Suggest process improvements based on task patterns.
    
    This analysis will help optimize task assignment and improve completion rates.
    """

@mcp.prompt()
def create_task_template(
    object_type: str,
    object_id: str,
    template_name: str
) -> str:
    """
    Generate a prompt for creating a set of template tasks for common scenarios.
    
    Args:
        object_type: Type of object to create tasks for (e.g., "incidents", "problems")
        object_id: ID of the object
        template_name: Name of template to use (e.g., "onboarding", "offboarding", "investigation")
    """
    return f"""
    Please help me create a set of standard tasks for {template_name} on {object_type}/{object_id}.
    
    First, let me get details about the {object_type} by using the resource at samanage://{object_type}/{object_id}.
    
    Based on the {template_name} template and the {object_type} details, please:
    
    1. Create an appropriate list of sequential tasks for this scenario.
    2. For each task, specify:
       - Task name
       - Description
       - Suggested assignee (based on roles if possible)
       - Priority
       - Estimated due date relative to creation (e.g., +1 day)
    
    3. Structure these tasks in a format ready for the batch_create_tasks tool.
    4. Include appropriate error handling and validation checks.
    
    After generating the tasks structure, I'll use the batch_create_tasks tool to create all tasks at once.
    """

# Tools for Comments

@mcp.tool()
async def search_comments(
    object_type: str,
    object_id: str,
    query: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    is_private: Optional[bool] = None
) -> str:
    """
    Search for comments with various filters.
    
    Args:
        object_type: Parent object type (e.g., "incidents", "problems", "changes")
        object_id: ID of the parent object
        query: Search term within comment body
        user_id: Filter by commenter user ID
        date_from: Filter by comment date (format: YYYY-MM-DD)
        date_to: Filter by comment date (format: YYYY-MM-DD)
        is_private: Filter by private status
    """
    # Get all comments for the object
    comments_response = await make_api_request(f"{object_type}/{object_id}/comments.json")
    
    # Filter comments based on criteria
    filtered_comments = []
    for comment in comments_response:
        # Check text search
        if query is not None:
            comment_body = comment.get("body", "")
            if query.lower() not in comment_body.lower():
                continue
        
        # Check user filter
        if user_id is not None:
            comment_user_id = comment.get("user", {}).get("id")
            if str(comment_user_id) != str(user_id):
                continue
        
        # Check date from filter
        if date_from is not None:
            comment_date = comment.get("created_at")
            if not comment_date or comment_date < date_from:
                continue
        
        # Check date to filter
        if date_to is not None:
            comment_date = comment.get("created_at")
            if not comment_date or comment_date > date_to:
                continue
        
        # Check private status filter
        if is_private is not None:
            comment_private = comment.get("is_private", False)
            if comment_private != is_private:
                continue
        
        # Comment passed all filters
        filtered_comments.append(comment)
    
    return json.dumps(filtered_comments, indent=2)

@mcp.tool()
async def analyze_comments(
    object_type: str,
    object_id: str,
    analyze_type: str = "summary"
) -> str:
    """
    Analyze comments for an object to extract insights.
    
    Args:
        object_type: Parent object type (e.g., "incidents", "problems", "changes")
        object_id: ID of the parent object
        analyze_type: Type of analysis ("summary", "activity", "participants")
    """
    # Get all comments for the object
    comments_response = await make_api_request(f"{object_type}/{object_id}/comments.json")
    
    # Get object details
    object_response = await make_api_request(f"{object_type}/{object_id}.json")
    
    if analyze_type == "summary":
        # Basic comment statistics
        total_comments = len(comments_response)
        private_comments = sum(1 for c in comments_response if c.get("is_private", False))
        public_comments = total_comments - private_comments
        
        # Calculate timespan
        comment_dates = [c.get("created_at") for c in comments_response if c.get("created_at")]
        
        timespan_days = 0
        if comment_dates and len(comment_dates) > 1:
            try:
                first_date = min(datetime.fromisoformat(date.replace('Z', '+00:00')) for date in comment_dates)
                last_date = max(datetime.fromisoformat(date.replace('Z', '+00:00')) for date in comment_dates)
                timespan_days = (last_date - first_date).days
            except (ValueError, TypeError):
                timespan_days = 0
        
        result = {
            "object_type": object_type,
            "object_id": object_id,
            "object_name": object_response.get("name", "Unknown"),
            "total_comments": total_comments,
            "private_comments": private_comments,
            "public_comments": public_comments,
            "timespan_days": timespan_days,
            "avg_comments_per_day": total_comments / timespan_days if timespan_days > 0 else 0
        }
    
    elif analyze_type == "activity":
        # Group comments by date
        comment_by_date = {}
        for comment in comments_response:
            created_at = comment.get("created_at")
            if not created_at:
                continue
                
            try:
                # Group by date only (no time)
                date_only = created_at.split('T')[0]
                
                if date_only not in comment_by_date:
                    comment_by_date[date_only] = 0
                    
                comment_by_date[date_only] += 1
            except Exception:
                continue
        
        # Convert to list of date-count pairs
        activity_data = [{"date": date, "count": count} for date, count in comment_by_date.items()]
        
        # Sort by date
        activity_data.sort(key=lambda x: x["date"])
        
        result = {
            "object_type": object_type,
            "object_id": object_id,
            "object_name": object_response.get("name", "Unknown"),
            "activity_data": activity_data
        }
    
    elif analyze_type == "participants":
        # Group comments by user
        comment_by_user = {}
        for comment in comments_response:
            user = comment.get("user", {})
            user_id = user.get("id")
            user_name = user.get("name", "Unknown")
            
            if not user_id:
                continue
                
            if user_id not in comment_by_user:
                comment_by_user[user_id] = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "comment_count": 0,
                    "private_count": 0
                }
                
            comment_by_user[user_id]["comment_count"] += 1
            
            if comment.get("is_private", False):
                comment_by_user[user_id]["private_count"] += 1
        
        # Convert to list and sort by comment count
        participants_data = list(comment_by_user.values())
        participants_data.sort(key=lambda x: x["comment_count"], reverse=True)
        
        result = {
            "object_type": object_type,
            "object_id": object_id,
            "object_name": object_response.get("name", "Unknown"),
            "total_participants": len(participants_data),
            "participants_data": participants_data
        }
    
    else:
        result = {
            "error": f"Unknown analysis type: {analyze_type}"
        }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_comment_with_mention(
    object_type: str,
    object_id: str,
    body: str,
    mentioned_user_ids: list[str],
    is_private: bool = False
) -> str:
    """
    Create a comment that @mentions specific users to notify them.
    
    Args:
        object_type: Parent object type (e.g., "incidents", "problems", "changes")
        object_id: ID of the parent object
        body: Text content of the comment
        mentioned_user_ids: List of user IDs to mention
        is_private: Whether the comment should be private
    """
    # First get user details for mentions
    mentioned_users = []
    for user_id in mentioned_user_ids:
        try:
            user_response = await make_api_request(f"users/{user_id}.json")
            mentioned_users.append({
                "id": user_id,
                "name": user_response.get("name", "Unknown User"),
                "email": user_response.get("email", "")
            })
        except Exception:
            # Skip if user not found
            pass
    
    # Build mention text to append to comment
    mention_text = ""
    if mentioned_users:
        mention_text = "\n\nCC: " + ", ".join(f"@{user['name']}" for user in mentioned_users)
    
    # Create comment with mentions
    comment_body = body + mention_text
    
    data = {
        "comment": {
            "body": comment_body,
            "is_private": str(is_private).lower()
        }
    }
    
    response = await make_api_request(
        f"{object_type}/{object_id}/comments.json", 
        method="POST", 
        data=data
    )
    
    return json.dumps(response, indent=2)

# Resources for Comments

@mcp.resource("samanage://comments/{object_type}/{object_id}/latest")
async def latest_comments_resource(object_type: str, object_id: str) -> str:
    """Get the latest comments for an object."""
    comments = await make_api_request(f"{object_type}/{object_id}/comments.json")
    
    # Sort by created_at (newest first)
    sorted_comments = sorted(
        comments,
        key=lambda c: c.get("created_at", ""),
        reverse=True
    )
    
    # Take top 5
    latest_comments = sorted_comments[:5]
    
    return json.dumps(latest_comments, indent=2)

@mcp.resource("samanage://comments/recent")
async def recent_comments_resource() -> str:
    """Get recent comments across all major object types."""
    object_types = ["incidents", "problems", "changes"]
    
    recent_comments = []
    for obj_type in object_types:
        # Get recent objects
        objects = await make_api_request(f"{obj_type}.json", params={"updated": "1d"})
        
        # Get comments for each object (limit to reduce API calls)
        for obj in objects[:5]:
            obj_id = obj.get("id")
            if not obj_id:
                continue
                
            comments = await make_api_request(f"{obj_type}/{obj_id}/comments.json")
            
            # Add object reference to each comment
            for comment in comments:
                comment["_object_type"] = obj_type
                comment["_object_id"] = obj_id
                comment["_object_name"] = obj.get("name", "Unknown")
                
                recent_comments.append(comment)
    
    # Sort by created_at (newest first)
    recent_comments.sort(
        key=lambda c: c.get("created_at", ""),
        reverse=True
    )
    
    # Take top 20
    return json.dumps(recent_comments[:20], indent=2)

# Prompts for Comments

@mcp.prompt()
def communication_analysis(
    object_type: str,
    object_id: str
) -> str:
    """
    Generate a prompt for analyzing communication patterns.
    
    Args:
        object_type: Object type to analyze (e.g., "incidents", "problems")
        object_id: ID of the object to analyze
    """
    return f"""
    Please analyze the communication patterns for {object_type} #{object_id}.
    
    I'll need to gather:
    1. Object details using the resource at samanage://{object_type}/{object_id}
    2. Comments using search_comments with object_type="{object_type}" and object_id="{object_id}"
    3. Comment activity analysis using analyze_comments with object_type="{object_type}", object_id="{object_id}", and analyze_type="activity"
    4. Participant analysis using analyze_comments with object_type="{object_type}", object_id="{object_id}", and analyze_type="participants"
    
    Once I have this data, please:
    
    1. Summarize the overall communication volume and patterns.
    2. Identify key participants and their roles in the conversation.
    3. Analyze the timing and frequency of communications.
    4. Detect any gaps in communication or response delays.
    5. Suggest communication improvements for similar future cases.
    
    This analysis will help improve our response efficiency and customer communication.
    """

@mcp.prompt()
def create_status_update(
    object_type: str,
    object_id: str,
    status: str
) -> str:
    """
    Generate a prompt for creating a standardized status update comment.
    
    Args:
        object_type: Object type to update (e.g., "incidents", "problems")
        object_id: ID of the object
        status: Status update type (e.g., "progress", "blocker", "resolution")
    """
    return f"""
    Please help me draft a professional status update comment for {object_type} #{object_id}.
    
    I'll first gather context:
    1. Current {object_type} details using the resource at samanage://{object_type}/{object_id}
    2. Latest comments using the resource at samanage://comments/{object_type}/{object_id}/latest
    
    Based on this context and the status type "{status}", please:
    
    1. Draft a clear, professional comment that provides a status update.
    2. Include appropriate details based on the {object_type}'s current state.
    3. For "progress" updates: focus on work completed and next steps.
    4. For "blocker" updates: clearly describe the issue and needed assistance.
    5. For "resolution" updates: explain the solution and any follow-up actions.
    
    Once drafted, suggest any users who should be mentioned in the comment and help me prepare to use the create_comment_with_mention tool.
    """

# Tools for Time Tracking

@mcp.tool()
async def generate_time_report(
    object_type: str,
    object_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
    group_by: str = "user"  # Options: "user", "date", "object"
) -> str:
    """
    Generate a time tracking report with various filters and groupings.
    
    Args:
        object_type: Object type for time entries (e.g., "incidents", "problems")
        object_id: Optional specific object ID (if None, reports across all objects)
        start_date: Start date for report range (format: YYYY-MM-DD)
        end_date: End date for report range (format: YYYY-MM-DD)
        user_id: Optional filter by specific user
        group_by: How to group the report results
    """
    # If object_id is provided, get time entries for that specific object
    if object_id:
        objects_to_check = [{
            "id": object_id,
            "type": object_type
        }]
    else:
        # Get all objects of the specified type
        objects_response = await make_api_request(f"{object_type}.json")
        objects_to_check = [{"id": obj.get("id"), "type": object_type} for obj in objects_response if obj.get("id")]
    
    # Collect all time entries
    all_time_entries = []
    
    # Limit the number of API calls for large collections
    for obj in objects_to_check[:20]:
        obj_id = obj["id"]
        obj_type = obj["type"]
        
        # Get time tracks for this object
        time_tracks = await make_api_request(f"{obj_type}/{obj_id}/time_tracks.json")
        
        # Get object details for reference
        obj_details = await make_api_request(f"{obj_type}/{obj_id}.json")
        
        # Add object information to each time entry
        for entry in time_tracks:
            entry["_object_id"] = obj_id
            entry["_object_type"] = obj_type
            entry["_object_name"] = obj_details.get("name", "Unknown")
            all_time_entries.append(entry)
    
    # Apply filters
    filtered_entries = []
    for entry in all_time_entries:
        # Filter by date range
        created_at = entry.get("created_at")
        if (start_date and created_at and created_at < start_date) or \
           (end_date and created_at and created_at > end_date):
            continue
        
        # Filter by user
        if user_id and entry.get("creator", {}).get("id") != user_id:
            continue
        
        filtered_entries.append(entry)
    
    # Group entries according to group_by parameter
    grouped_data = {}
    
    if group_by == "user":
        # Group by user
        for entry in filtered_entries:
            creator = entry.get("creator", {})
            creator_id = creator.get("id")
            creator_name = creator.get("name", "Unknown")
            
            if not creator_id:
                continue
                
            if creator_id not in grouped_data:
                grouped_data[creator_id] = {
                    "user_id": creator_id,
                    "user_name": creator_name,
                    "total_minutes": 0,
                    "entry_count": 0,
                    "objects": {}
                }
            
            # Add minutes
            minutes = int(entry.get("minutes", 0))
            grouped_data[creator_id]["total_minutes"] += minutes
            grouped_data[creator_id]["entry_count"] += 1
            
            # Track by object
            obj_id = entry["_object_id"]
            obj_name = entry["_object_name"]
            
            if obj_id not in grouped_data[creator_id]["objects"]:
                grouped_data[creator_id]["objects"][obj_id] = {
                    "object_id": obj_id,
                    "object_name": obj_name,
                    "minutes": 0
                }
                
            grouped_data[creator_id]["objects"][obj_id]["minutes"] += minutes
        
        # Convert objects dict to list for each user
        for user_id, user_data in grouped_data.items():
            user_data["objects"] = list(user_data["objects"].values())
            # Sort objects by time
            user_data["objects"].sort(key=lambda x: x["minutes"], reverse=True)
    
    elif group_by == "date":
        # Group by date
        for entry in filtered_entries:
            created_at = entry.get("created_at", "")
            
            # Group by date (no time)
            if not created_at:
                continue
                
            date_only = created_at.split("T")[0]
            
            if date_only not in grouped_data:
                grouped_data[date_only] = {
                    "date": date_only,
                    "total_minutes": 0,
                    "entry_count": 0,
                    "users": {}
                }
            
            # Add minutes
            minutes = int(entry.get("minutes", 0))
            grouped_data[date_only]["total_minutes"] += minutes
            grouped_data[date_only]["entry_count"] += 1
            
            # Track by user
            creator = entry.get("creator", {})
            creator_id = creator.get("id")
            creator_name = creator.get("name", "Unknown")
            
            if not creator_id:
                continue
                
            if creator_id not in grouped_data[date_only]["users"]:
                grouped_data[date_only]["users"][creator_id] = {
                    "user_id": creator_id,
                    "user_name": creator_name,
                    "minutes": 0
                }
                
            grouped_data[date_only]["users"][creator_id]["minutes"] += minutes
        
        # Convert users dict to list for each date
        for date, date_data in grouped_data.items():
            date_data["users"] = list(date_data["users"].values())
            # Sort users by time
            date_data["users"].sort(key=lambda x: x["minutes"], reverse=True)
    
    elif group_by == "object":
        # Group by object
        for entry in filtered_entries:
            obj_id = entry["_object_id"]
            obj_type = entry["_object_type"]
            obj_name = entry["_object_name"]
            
            obj_key = f"{obj_type}_{obj_id}"
            
            if obj_key not in grouped_data:
                grouped_data[obj_key] = {
                    "object_id": obj_id,
                    "object_type": obj_type,
                    "object_name": obj_name,
                    "total_minutes": 0,
                    "entry_count": 0,
                    "users": {}
                }
            
            # Add minutes
            minutes = int(entry.get("minutes", 0))
            grouped_data[obj_key]["total_minutes"] += minutes
            grouped_data[obj_key]["entry_count"] += 1
            
            # Track by user
            creator = entry.get("creator", {})
            creator_id = creator.get("id")
            creator_name = creator.get("name", "Unknown")
            
            if not creator_id:
                continue
                
            if creator_id not in grouped_data[obj_key]["users"]:
                grouped_data[obj_key]["users"][creator_id] = {
                    "user_id": creator_id,
                    "user_name": creator_name,
                    "minutes": 0
                }
                
            grouped_data[obj_key]["users"][creator_id]["minutes"] += minutes
        
        # Convert users dict to list for each object
        for obj_key, obj_data in grouped_data.items():
            obj_data["users"] = list(obj_data["users"].values())
            # Sort users by time
            obj_data["users"].sort(key=lambda x: x["minutes"], reverse=True)
    
    # Convert grouped data to list
    result_list = list(grouped_data.values())
    
    # Sort by total time
    result_list.sort(key=lambda x: x["total_minutes"], reverse=True)
    
    # Calculate summary
    summary = {
        "total_time_entries": len(filtered_entries),
        "total_minutes": sum(int(entry.get("minutes", 0)) for entry in filtered_entries),
        "total_objects": len(set(entry["_object_id"] for entry in filtered_entries)),
        "total_users": len(set(entry.get("creator", {}).get("id") for entry in filtered_entries if entry.get("creator", {}).get("id"))),
        "group_by": group_by,
        "filters": {
            "object_type": object_type,
            "object_id": object_id,
            "start_date": start_date,
            "end_date": end_date,
            "user_id": user_id
        }
    }
    
    result = {
        "summary": summary,
        "data": result_list
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def bulk_add_time_tracks(
    object_type: str,
    object_id: Union[str, int],
    time_entries: List[Dict[str, Any]]
) -> str:
    """
    Add multiple time track entries to an object.
    
    Args:
        object_type: Parent object type (e.g., "incidents", "problems", "changes")
        object_id: ID of the parent object
        time_entries: List of time entry objects with name, minutes_parsed, etc.
    """
    # Convert object ID to string
    object_id_str = ensure_string_id(object_id)
    
    results = []
    errors = []
    
    for entry_data in time_entries:
        try:
            # Create time track payload
            track_payload = {"time_track": entry_data}
            
            # Create time track
            response = await make_api_request(
                f"{object_type}/{object_id_str}/time_tracks.json",
                method="POST",
                data=track_payload
            )
            
            results.append({
                "status": "success",
                "time_track": response
            })
        except Exception as e:
            errors.append({
                "status": "error",
                "entry_data": entry_data,
                "error": str(e)
            })
    
    return json.dumps({
        "successful_entries": len(results),
        "failed_entries": len(errors),
        "results": results,
        "errors": errors
    }, indent=2)

# Resources for Time Tracking

@mcp.resource("samanage://time-tracks/by-user/{user_id}")
async def time_tracks_by_user_resource(user_id: str) -> str:
    """Get recent time entries for a specific user."""
    object_types = ["incidents", "problems", "changes"]
    
    user_time_entries = []
    for obj_type in object_types:
        # Get objects of this type
        objects = await make_api_request(f"{obj_type}.json", params={"updated": "30d"})
        
        # Get time tracks for each object (limit to reduce API calls)
        for obj in objects[:10]:
            obj_id = obj.get("id")
            if not obj_id:
                continue
                
            time_tracks = await make_api_request(f"{obj_type}/{obj_id}/time_tracks.json")
            
            # Filter by user and add object reference
            for track in time_tracks:
                if track.get("creator", {}).get("id") == user_id:
                    # Add object reference
                    track["_object_type"] = obj_type
                    track["_object_id"] = obj_id
                    track["_object_name"] = obj.get("name", "Unknown")
                    
                    user_time_entries.append(track)
    
    # Sort by created_at (newest first)
    user_time_entries.sort(
        key=lambda t: t.get("created_at", ""),
        reverse=True
    )
    
    return json.dumps(user_time_entries, indent=2)

@mcp.resource("samanage://time-tracks/summary")
async def time_tracks_summary_resource() -> str:
    """Get a summary of recent time tracking activity."""
    object_types = ["incidents", "problems", "changes"]
    
    # Data collection
    time_entries = []
    for obj_type in object_types:
        # Get recent objects
        objects = await make_api_request(f"{obj_type}.json", params={"updated": "14d"})
        
        # Get time tracks for each object (limit to reduce API calls)
        for obj in objects[:10]:
            obj_id = obj.get("id")
            if not obj_id:
                continue
                
            time_tracks = await make_api_request(f"{obj_type}/{obj_id}/time_tracks.json")
            
            # Add object reference to each entry
            for track in time_tracks:
                track["_object_type"] = obj_type
                track["_object_id"] = obj_id
                track["_object_name"] = obj.get("name", "Unknown")
                
                time_entries.append(track)
    
    # Process data for summary
    total_minutes = sum(int(entry.get("minutes", 0)) for entry in time_entries)
    
    # Group by user
    user_stats = {}
    for entry in time_entries:
        creator = entry.get("creator", {})
        creator_id = creator.get("id")
        creator_name = creator.get("name", "Unknown")
        
        if not creator_id:
            continue
            
        if creator_id not in user_stats:
            user_stats[creator_id] = {
                "user_id": creator_id,
                "user_name": creator_name,
                "total_minutes": 0,
                "entry_count": 0
            }
            
        user_stats[creator_id]["total_minutes"] += int(entry.get("minutes", 0))
        user_stats[creator_id]["entry_count"] += 1
    
    # Group by object type
    type_stats = {}
    for entry in time_entries:
        obj_type = entry["_object_type"]
        
        if obj_type not in type_stats:
            type_stats[obj_type] = {
                "object_type": obj_type,
                "total_minutes": 0,
                "entry_count": 0
            }
            
        type_stats[obj_type]["total_minutes"] += int(entry.get("minutes", 0))
        type_stats[obj_type]["entry_count"] += 1
    
    # Create summary
    summary = {
        "total_time_entries": len(time_entries),
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "unique_users": len(user_stats),
        "unique_objects": len(set((entry["_object_type"], entry["_object_id"]) for entry in time_entries)),
        "by_user": list(user_stats.values()),
        "by_type": list(type_stats.values())
    }
    
    # Sort users by time
    summary["by_user"].sort(key=lambda x: x["total_minutes"], reverse=True)
    
    # Sort types by time
    summary["by_type"].sort(key=lambda x: x["total_minutes"], reverse=True)
    
    return json.dumps(summary, indent=2)

# Prompts for Time Tracking

@mcp.prompt()
def resource_utilization_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Generate a prompt for analyzing resource utilization.
    
    Args:
        start_date: Optional start date for analysis (format: YYYY-MM-DD)
        end_date: Optional end date for analysis (format: YYYY-MM-DD)
    """
    date_range = ""
    if start_date and end_date:
        date_range = f"from {start_date} to {end_date}"
    elif start_date:
        date_range = f"since {start_date}"
    elif end_date:
        date_range = f"until {end_date}"
    else:
        date_range = "for the recent period"
    
    return f"""
    Please analyze staff resource utilization and time allocation {date_range}.
    
    I'll need to gather:
    1. Time tracking summary using the resource at samanage://time-tracks/summary
    2. Detailed time reports for incidents using generate_time_report with object_type="incidents", group_by="user", start_date="{start_date}", end_date="{end_date}"
    3. Detailed time reports for problems using generate_time_report with object_type="problems", group_by="user", start_date="{start_date}", end_date="{end_date}"
    
    Once I have this data, please:
    
    1. Summarize overall time tracking metrics and patterns.
    2. Analyze the distribution of time across different object types.
    3. Identify the most time-intensive objects and activities.
    4. Compare time allocation across different users and teams.
    5. Calculate utilization rates and efficiency metrics.
    6. Recommend resource balancing or optimization strategies.
    
    This analysis will help improve resource planning and workload distribution.
    """

@mcp.prompt()
def time_entry_template(
    object_type: str,
    object_id: str,
    activity_type: str
) -> str:
    """
    Generate a prompt for creating standardized time entries.
    
    Args:
        object_type: Type of object (e.g., "incidents", "problems")
        object_id: ID of the object
        activity_type: Type of activity (e.g., "research", "development", "testing", "communication")
    """
    return f"""
    Please help me create standardized time entries for {activity_type} activities on {object_type} #{object_id}.
    
    I'll first gather context about the {object_type} using the resource at samanage://{object_type}/{object_id}.
    
    Based on the {activity_type} activity type and the {object_type} details, please:
    
    1. Suggest appropriate time entries that cover common {activity_type} tasks.
    2. For each entry, recommend:
       - A clear, descriptive name
       - Appropriate time duration based on typical {activity_type} tasks
       - Any relevant categories or tags
    
    3. Structure these entries in a format ready for the bulk_add_time_tracks tool.
    4. Include a mix of entries that reflect realistic work breakdown.
    
    After generating the time entry templates, I'll use the bulk_add_time_tracks tool to record all entries at once.
    """

@mcp.tool()
async def update_incident(
    incident_id: Union[str, int],
    name: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    state: Optional[str] = None,
    assignee_email: Optional[str] = None,
) -> str:
    """
    Update an existing incident with robust type conversion and error handling.
    """
    # Ensure incident_id is a string
    incident_id_str = ensure_string_id(incident_id)
    
    # Validate state if provided
    valid_states = ["New", "In Progress", "Resolved", "Closed"]
    if state and state not in valid_states:
        return json.dumps({
            "error": "Invalid state",
            "valid_states": valid_states
        }, indent=2)
    
    # Prepare update payload
    data = {"incident": {}}
    
    if name:
        data["incident"]["name"] = name
    
    if description:
        data["incident"]["description"] = description
    
    if priority:
        data["incident"]["priority"] = priority
    
    if state:
        data["incident"]["state"] = state
    
    if assignee_email:
        data["incident"]["assignee"] = {"email": assignee_email}
    
    try:
        response = await make_api_request(
            f"incidents/{incident_id_str}.json", 
            method="PUT", 
            data=data
        )
        return json.dumps(response, indent=2)
    except ValueError as e:
        return json.dumps({
            "error": "Incident update failed",
            "details": str(e)
        }, indent=2)
    

@mcp.tool()
async def update_incident_category(
    incident_id: Union[str, int],  # Accept both string and int
    category_id: int,
    subcategory_id: Optional[int] = None
) -> str:
    """Update an incident's category and subcategory."""
    # Use the helper
    incident_id_str = ensure_string_id(incident_id)
    
    # Rest of the function...
    data = {
        "incident": {
            "category_id": category_id
        }
    }
    
    if subcategory_id:
        data["incident"]["subcategory_id"] = subcategory_id
        
    try:
        response = await make_api_request(f"incidents/{incident_id_str}.json", method="PUT", data=data)
        return json.dumps(response, indent=2)
    except ValueError as e:
        return json.dumps({
            "error": "Category update failed",
            "details": str(e)
        }, indent=2)
    
@mcp.tool()
async def update_incident_location(
    incident_id: str,
    site_id: Optional[int] = None,
    department_id: Optional[int] = None
) -> str:
    """Update an incident's site and department.
    
    Args:
        incident_id: ID of the incident to update
        site_id: ID of the site
        department_id: ID of the department
    """
    # Ensure incident_id is a string
    incident_id_str = ensure_string_id(incident_id)
    
    data = {"incident": {}}
    
    if site_id:
        data["incident"]["site_id"] = site_id
    
    if department_id:
        data["incident"]["department_id"] = department_id
        
    try:
        response = await make_api_request(f"incidents/{incident_id_str}.json", method="PUT", data=data)
        return json.dumps(response, indent=2)
    except ValueError as e:
        return json.dumps({
            "error": "Location update failed",
            "details": str(e)
        }, indent=2)
    
@mcp.tool()
async def search_users(
    query: Optional[str] = None,
    email: Optional[str] = None,
    role_id: Optional[int] = None,
    site_id: Optional[int] = None,
    department_id: Optional[int] = None
) -> str:
    """Search for users with various filters.
    
    Args:
        query: Text to search in user name and email
        email: Filter by exact email match
        role_id: Filter by role ID
        site_id: Filter by site ID
        department_id: Filter by department ID
    """
    params = {}
    
    if query:
        params["query"] = query
    
    if email:
        params["email"] = email
    
    if role_id:
        params["role_id"] = role_id
    
    if site_id:
        params["site_id"] = site_id
    
    if department_id:
        params["department_id"] = department_id
        
    response = await make_api_request("users.json", params=params)
    return json.dumps(response, indent=2)

@mcp.tool()
async def get_user_details(
    user_id: Union[str, int]  # Accept both string and int
) -> str:
    """Get detailed information about a specific user.
    
    Args:
        user_id: ID of the user
    """
    try:
        # Ensure user_id is a string
        user_id_str = str(user_id)
        
        # Remove any domain prefix if present
        if "-" in user_id_str:
            user_id_str = user_id_str.split("-")[0]
            
        response = await make_api_request(f"users/{user_id_str}.json")
        return json.dumps(response, indent=2)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return f"Error: User with ID {user_id} not found. Please verify the user ID exists and try again."
        return f"Error getting user details: {error_msg}"
@mcp.tool()
async def assign_role_to_user(
    user_id: Union[str, int],
    role_id: Union[str, int]
) -> str:
    """
    Assign a role to a user with improved type conversion.
    """
    try:
        # Ensure IDs are converted to strings
        user_id_str = ensure_string_id(user_id)
        role_id_str = ensure_string_id(role_id)

        data = {
            "user": {
                "role": {
                    "id": role_id_str
                }
            }
        }
        
        response = await make_api_request(f"users/{user_id_str}.json", method="PUT", data=data)
        return json.dumps(response, indent=2)
    except ValueError as e:
        return json.dumps({
            "error": "Role assignment failed",
            "details": str(e)
        }, indent=2)

@mcp.tool()
async def get_user_details(
    user_id: Union[str, int]
) -> str:
    """
    Retrieve user details with robust ID handling.
    """
    try:
        # Ensure user_id is a string
        user_id_str = ensure_string_id(user_id)
        
        response = await make_api_request(f"users/{user_id_str}.json")
        return json.dumps(response, indent=2)
    except ValueError as e:
        return json.dumps({
            "error": "User retrieval failed",
            "details": str(e)
        }, indent=2)
    
@mcp.tool()
async def list_departments() -> str:
    """Get a list of all departments."""
    response = await make_api_request("departments.json")
    return json.dumps(response, indent=2)

@mcp.tool()
async def list_sites() -> str:
    """Get a list of all sites."""
    response = await make_api_request("sites.json")
    return json.dumps(response, indent=2)

@mcp.tool()
async def list_roles() -> str:
    """Get a list of all roles."""
    response = await make_api_request("roles.json")
    return json.dumps(response, indent=2)

@mcp.tool()
async def vote_on_solution(
    solution_id: int,
    vote: bool  # True for upvote, False for downvote
) -> str:
    """
    Vote on a solution's helpfulness.
    
    Args:
        solution_id: ID of the solution
        vote: True for upvote, False for downvote
    """
    vote_type = "up" if vote else "down"
    
    try:
        # Convert solution_id to string and ensure it's valid
        solution_id_str = str(solution_id)
        
        response = await make_api_request(
            f"solutions/{solution_id_str}/votes/{vote_type}.json", 
            method="POST",
            data={}
        )
        return json.dumps(response, indent=2)
    except Exception as e:
        error_msg = str(e)
        # Check if it's a 404 and give a more helpful message
        if "404" in error_msg:
            return f"Error: Solution with ID {solution_id} not found. Please check the solution ID and try again."
        return f"Error voting on solution: {error_msg}"

@mcp.tool()
async def get_state_options() -> str:
    """Get a list of available state options for incidents."""
    # This is a static helper that doesn't require an API call
    states = {
        "New": "For newly created incidents",
        "In Progress": "For incidents being worked on",
        "Resolved": "For incidents that have been fixed",
        "Closed": "For incidents that are completed"
    }
    return json.dumps(states, indent=2)

@mcp.tool()
async def get_categories() -> str:
    """Get a list of all categories and subcategories."""
    response = await make_api_request("categories.json")
    return json.dumps(response, indent=2)






    # Add these improved utility functions to your server.py file

# Improved API request function with better error handling and response formatting
async def make_api_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Make a request to the SolarWinds Service Desk API with improved error handling and response formatting.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method (GET, POST, PUT, DELETE)
        params: Query parameters
        data: Request body data
        
    Returns:
        Parsed JSON response with consistent formatting
    """
    # Normalize the endpoint if needed
    if endpoint.startswith('/'):
        endpoint = endpoint[1:]
        
    # Gracefully handle empty parameters or data
    if params is not None:
        # Remove None values from params
        params = {k: v for k, v in params.items() if v is not None}
    
    # Clean up data if it exists, removing None values
    if data is not None:
        # Use a recursive function to clean the data
        def clean_dict(d):
            if not isinstance(d, dict):
                return d
            return {
                k: clean_dict(v) if isinstance(v, dict) else v
                for k, v in d.items()
                if v is not None
            }
        data = clean_dict(data)
    
    async with await get_client() as client:
        try:
            # Handle API Token not configured scenario with enhanced mock data
            if not API_TOKEN and not endpoint.startswith("test"):
                logger.warning(f"Simulating API call to {endpoint} (demo mode)")
                
                # Return more detailed mock data instead of making a real API call
                if endpoint.endswith("incidents.json"):
                    return [
                        {
                            "id": "123", 
                            "name": "Database Server Offline", 
                            "state": "In Progress", 
                            "priority": "High",
                            "description": "The main database server is not responding to connection requests.",
                            "created_at": datetime.datetime.now().isoformat(),
                            "updated_at": datetime.datetime.now().isoformat(),
                            "assignee": {"id": "456", "name": "Nagarjuna Kumar", "email": "nagarjuna.kumar@example.com"},
                            "requester": {"id": "789", "name": "Finance Department", "email": "finance@example.com"},
                            "department": {"id": "101", "name": "Finance"},
                            "site": {"id": "201", "name": "Headquarters"}
                        },
                        {
                            "id": "124", 
                            "name": "Network Outage - Branch Office", 
                            "state": "New", 
                            "priority": "Critical",
                            "description": "The branch office has lost network connectivity. Users cannot access any systems.",
                            "created_at": (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(),
                            "updated_at": (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(),
                            "requester": {"id": "790", "name": "Branch Manager", "email": "branch.manager@example.com"},
                            "department": {"id": "102", "name": "Operations"},
                            "site": {"id": "202", "name": "Branch Office"}
                        }
                    ]
                elif endpoint.endswith("users.json"):
                    return [
                        {"id": "456", "name": "Nagarjuna Kumar", "email": "nagarjuna.kumar@example.com", "role": {"id": "1", "name": "Admin"}},
                        {"id": "789", "name": "Finance Department", "email": "finance@example.com", "role": {"id": "2", "name": "User"}},
                        {"id": "790", "name": "Branch Manager", "email": "branch.manager@example.com", "role": {"id": "3", "name": "Manager"}}
                    ]
                elif "incidents" in endpoint and ".json" in endpoint and "123" in endpoint:
                    return {
                        "id": "123", 
                        "name": "Database Server Offline", 
                        "state": "In Progress", 
                        "priority": "High",
                        "description": "The main database server is not responding to connection requests. IT team is investigating the cause, which appears to be related to a memory leak in the connection pool.",
                        "created_at": datetime.datetime.now().isoformat(),
                        "updated_at": datetime.datetime.now().isoformat(),
                        "assignee": {"id": "456", "name": "Nagarjuna Kumar", "email": "nagarjuna.kumar@example.com"},
                        "requester": {"id": "789", "name": "Finance Department", "email": "finance@example.com"},
                        "department": {"id": "101", "name": "Finance"},
                        "site": {"id": "201", "name": "Headquarters"},
                        "comments": [
                            {
                                "id": "901",
                                "body": "Initial investigation shows a potential memory leak in the database connection pool.",
                                "is_private": False,
                                "created_at": (datetime.datetime.now() - datetime.timedelta(minutes=30)).isoformat(),
                                "user": {"id": "456", "name": "Nagarjuna Kumar"}
                            }
                        ]
                    }
                elif "problems" in endpoint and ".json" in endpoint:
                    return [
                        {
                            "id": "456", 
                            "name": "Recurring Database Performance Issues", 
                            "state": "Open", 
                            "priority": "High",
                            "description": "Database servers have been experiencing performance degradation during peak hours.",
                            "created_at": (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat(),
                            "updated_at": (datetime.datetime.now() - datetime.timedelta(hours=5)).isoformat(),
                            "assignee": {"id": "456", "name": "Nagarjuna Kumar", "email": "nagarjuna.kumar@example.com"}
                        }
                    ]
                elif "departments" in endpoint and ".json" in endpoint:
                    return [
                        {"id": "101", "name": "Finance", "description": "Finance department"},
                        {"id": "102", "name": "Operations", "description": "Operations department"},
                        {"id": "103", "name": "IT", "description": "Information Technology department"},
                        {"id": "104", "name": "HR", "description": "Human Resources department"}
                    ]
                elif "sites" in endpoint and ".json" in endpoint:
                    return [
                        {"id": "201", "name": "Headquarters", "address": "123 Main St"},
                        {"id": "202", "name": "Branch Office", "address": "456 Oak Ave"},
                        {"id": "203", "name": "Data Center", "address": "789 Server Lane"}
                    ]
                elif "categories" in endpoint and ".json" in endpoint:
                    return [
                        {"id": "301", "name": "Hardware", "parent_id": None},
                        {"id": "302", "name": "Software", "parent_id": None},
                        {"id": "303", "name": "Network", "parent_id": None},
                        {"id": "304", "name": "Database", "parent_id": "302"},
                        {"id": "305", "name": "Server", "parent_id": "301"}
                    ]
                elif endpoint.endswith("comments.json") and "123" in endpoint:
                    return [
                        {
                            "id": "901",
                            "body": "Initial investigation shows a potential memory leak in the database connection pool.",
                            "is_private": False,
                            "created_at": (datetime.datetime.now() - datetime.timedelta(minutes=30)).isoformat(),
                            "user": {"id": "456", "name": "Nagarjuna Kumar"}
                        }
                    ]
                elif "time_tracks" in endpoint and ".json" in endpoint:
                    return [
                        {
                            "id": "601",
                            "name": "Root cause analysis",
                            "minutes": 180,
                            "created_at": (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat(),
                            "creator": {"id": "456", "name": "Nagarjuna Kumar"}
                        },
                        {
                            "id": "602",
                            "name": "Patch preparation",
                            "minutes": 120,
                            "created_at": (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(),
                            "creator": {"id": "456", "name": "Nagarjuna Kumar"}
                        }
                    ]
                elif "solutions" in endpoint and ".json" in endpoint:
                    return [
                        {
                            "id": "701",
                            "title": "Resolving Database Connection Pool Memory Leaks",
                            "description": "Steps for identifying and resolving memory leaks in database connection pools.",
                            "state": "Published",
                            "created_at": (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
                            "creator": {"id": "456", "name": "Nagarjuna Kumar"}
                        }
                    ]
                else:
                    return []
                    
            # Prepare debug info
            request_info = {
                "method": method,
                "endpoint": endpoint,
                "params": params,
                "data": data
            }
            logger.debug(f"API Request: {json.dumps(request_info)}")
            
            # Make the actual API call
            if method == "GET":
                response = await client.get(endpoint, params=params)
            elif method == "POST":
                response = await client.post(endpoint, json=data, params=params)
            elif method == "PUT":
                response = await client.put(endpoint, json=data, params=params)
            elif method == "DELETE":
                response = await client.delete(endpoint, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Log the response status
            logger.debug(f"API Response Status: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            # Format the response consistently
            if isinstance(result, dict) and "errors" in result:
                logger.warning(f"API returned errors: {result['errors']}")
                
            return result
            
        except httpx.HTTPStatusError as e:
            # Improved error logging
            error_detail = f"API request failed: {e.response.status_code}"
            try:
                error_json = e.response.json()
                error_detail += f" - {json.dumps(error_json)}"
            except:
                error_detail += f" - {e.response.text}"
            
            logger.error(f"HTTP Error: {error_detail}")
            
            # Create a more helpful error response
            error_response = {
                "error": True,
                "status_code": e.response.status_code,
                "message": str(e),
                "details": error_detail,
                "endpoint": endpoint,
                "time": datetime.datetime.now().isoformat()
            }
            
            return error_response
            
        except httpx.RequestError as e:
            logger.error(f"Network error: {str(e)}")
            
            error_response = {
                "error": True,
                "type": "network_error",
                "message": str(e),
                "endpoint": endpoint,
                "time": datetime.datetime.now().isoformat()
            }
            
            return error_response
            
        except Exception as e:
            logger.error(f"Unexpected error making API request: {str(e)}")
            
            error_response = {
                "error": True,
                "type": "unexpected_error",
                "message": str(e),
                "endpoint": endpoint,
                "time": datetime.datetime.now().isoformat()
            }
            
            return error_response

# Enhanced fuzzy matching function for more forgiving parameter matching
def fuzzy_match_parameter(input_value: str, valid_values: List[str], threshold: float = 0.7) -> Optional[str]:
    """
    Find the closest match for an input value in a list of valid values with enhanced matching.
    
    Args:
        input_value: The input string to match
        valid_values: List of valid string values to match against
        threshold: Minimum similarity score (0-1) to consider a match
        
    Returns:
        The closest matching valid value, or None if no match meets the threshold
    """
    if not input_value or not valid_values:
        return None
        
    # For case-insensitive matching
    input_lower = input_value.lower()
    valid_lower = [v.lower() for v in valid_values]
    
    # Check for exact matches first
    if input_lower in valid_lower:
        index = valid_lower.index(input_lower)
        return valid_values[index]
    
    # Check for matches on word stems (e.g., "progress" matching "in progress")
    for i, valid in enumerate(valid_lower):
        words = valid.split()
        for word in words:
            if input_lower == word or input_lower in word or word in input_lower:
                # Higher weight for stem matches
                return valid_values[i]
    
    # Use difflib for fuzzy matching
    from difflib import get_close_matches
    matches = get_close_matches(input_lower, valid_lower, n=1, cutoff=threshold)
    
    if matches:
        index = valid_lower.index(matches[0])
        return valid_values[index]
    
    return None

# New function for improved incident update
@mcp.tool()
async def update_incident_with_details(
    incident_id: Union[str, int],
    updates: Dict[str, Any]
) -> str:
    """
    Update an incident with multiple fields in a single call.
    
    Args:
        incident_id: ID of the incident to update
        updates: Dictionary of field updates (name, description, priority, state, assignee_email, etc.)
    """
    # Ensure incident_id is a string
    incident_id_str = ensure_string_id(incident_id)
    
    # Prepare update payload
    data = {"incident": {}}
    
    # Map updates to API fields
    for key, value in updates.items():
        if key in ["name", "description", "priority", "state", "due_at"]:
            # Direct field mapping
            data["incident"][key] = value
        elif key == "assignee_email":
            # Handle assignee update
            data["incident"]["assignee"] = {"email": value}
        elif key == "requester_email":
            # Handle requester update
            data["incident"]["requester"] = {"email": value}
        elif key == "department_id":
            # Handle department update
            data["incident"]["department_id"] = value
        elif key == "site_id":
            # Handle site update
            data["incident"]["site_id"] = value
        elif key == "category_id":
            # Handle category update
            data["incident"]["category_id"] = value
        elif key == "subcategory_id":
            # Handle subcategory update
            data["incident"]["subcategory_id"] = value
    
    # Apply value normalization for common fields
    if "state" in data["incident"]:
        valid_states = ["New", "Open", "In Progress", "Pending", "Resolved", "Closed"]
        state_value = data["incident"]["state"]
        corrected_state = fuzzy_match_parameter(state_value, valid_states)
        if corrected_state and corrected_state != state_value:
            logger.info(f"Corrected state value from '{state_value}' to '{corrected_state}'")
            data["incident"]["state"] = corrected_state
    
    if "priority" in data["incident"]:
        valid_priorities = ["Low", "Medium", "High", "Critical"]
        priority_value = data["incident"]["priority"]
        corrected_priority = fuzzy_match_parameter(priority_value, valid_priorities)
        if corrected_priority and corrected_priority != priority_value:
            logger.info(f"Corrected priority value from '{priority_value}' to '{corrected_priority}'")
            data["incident"]["priority"] = corrected_priority
    
    try:
        response = await make_api_request(
            f"incidents/{incident_id_str}.json", 
            method="PUT", 
            data=data
        )
        
        # Enhanced logging for successful updates
        if not (isinstance(response, dict) and response.get("error")):
            logger.info(f"Successfully updated incident {incident_id_str}")
            
            # Add user-friendly success message to response
            if isinstance(response, dict):
                response["_system_message"] = f"Incident #{incident_id_str} was successfully updated."
        
        return json.dumps(response, indent=2)
    except Exception as e:
        error_msg = str(e)
        return json.dumps({
            "error": True,
            "message": "Incident update failed",
            "details": error_msg,
            "_system_message": f"Failed to update incident #{incident_id_str}: {error_msg}"
        }, indent=2)

# New comprehensive function for incident resolution with comments
@mcp.tool()
async def resolve_incident_with_details(
    incident_id: Union[str, int],
    resolution_summary: str,
    add_comment: bool = True,
    resolution_category_id: Optional[int] = None,
    time_spent_minutes: Optional[int] = None
) -> str:
    """
    Resolve an incident with comprehensive details in a single call.
    
    Args:
        incident_id: ID of the incident to resolve
        resolution_summary: Summary of how the issue was resolved
        add_comment: Whether to add the resolution summary as a comment
        resolution_category_id: Optional category ID for the resolution
        time_spent_minutes: Optional time spent on resolution to track
    """
    # Ensure incident_id is a string
    incident_id_str = ensure_string_id(incident_id)
    
    # Prepare the resolution response
    results = {
        "incident_update": None,
        "comment_added": None,
        "time_tracked": None,
        "status": "success"
    }
    
    # Step 1: Update the incident state to Resolved
    update_data = {
        "incident": {
            "state": "Resolved"
        }
    }
    
    if resolution_category_id:
        update_data["incident"]["resolution_category_id"] = resolution_category_id
    
    try:
        incident_response = await make_api_request(
            f"incidents/{incident_id_str}.json", 
            method="PUT", 
            data=update_data
        )
        
        if isinstance(incident_response, dict) and incident_response.get("error"):
            results["status"] = "partial_failure"
            results["incident_update"] = {
                "status": "error",
                "details": incident_response
            }
        else:
            results["incident_update"] = {
                "status": "success",
                "details": incident_response
            }
        
        # Step 2: Add resolution comment if requested
        if add_comment:
            comment_data = {
                "comment": {
                    "body": f"Resolution Summary: {resolution_summary}",
                    "is_private": False
                }
            }
            
            try:
                comment_response = await make_api_request(
                    f"incidents/{incident_id_str}/comments.json", 
                    method="POST", 
                    data=comment_data
                )
                
                if isinstance(comment_response, dict) and comment_response.get("error"):
                    results["status"] = "partial_failure"
                    results["comment_added"] = {
                        "status": "error",
                        "details": comment_response
                    }
                else:
                    results["comment_added"] = {
                        "status": "success",
                        "details": comment_response
                    }
            except Exception as e:
                results["status"] = "partial_failure"
                results["comment_added"] = {
                    "status": "error",
                    "message": str(e)
                }
        
        # Step 3: Add time tracking if requested
        if time_spent_minutes:
            time_data = {
                "time_track": {
                    "name": "Resolution implementation",
                    "minutes": time_spent_minutes
                }
            }
            
            try:
                time_response = await make_api_request(
                    f"incidents/{incident_id_str}/time_tracks.json", 
                    method="POST", 
                    data=time_data
                )
                
                if isinstance(time_response, dict) and time_response.get("error"):
                    results["status"] = "partial_failure"
                    results["time_tracked"] = {
                        "status": "error",
                        "details": time_response
                    }
                else:
                    results["time_tracked"] = {
                        "status": "success",
                        "details": time_response
                    }
            except Exception as e:
                results["status"] = "partial_failure"
                results["time_tracked"] = {
                    "status": "error",
                    "message": str(e)
                }
        
        # Add a user-friendly summary message
        results["_system_message"] = f"Incident #{incident_id_str} has been resolved. "
        if results["status"] == "success":
            results["_system_message"] += "All operations completed successfully."
        else:
            results["_system_message"] += "Some operations encountered issues. See details for more information."
            
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "failure",
            "message": f"Failed to resolve incident: {str(e)}",
            "_system_message": f"Failed to resolve incident #{incident_id_str}: {str(e)}"
        }, indent=2)

# New comprehensive function for linking incidents to problems
@mcp.tool()
async def link_incidents_to_problem(
    problem_id: Union[str, int],
    incident_ids: List[Union[str, int]],
    add_comments: bool = True
) -> str:
    """
    Link multiple incidents to a problem record.
    
    Args:
        problem_id: ID of the problem record
        incident_ids: List of incident IDs to link
        add_comments: Whether to add comments to the incidents about the link
    """
    # Ensure IDs are strings
    problem_id_str = ensure_string_id(problem_id)
    incident_id_strs = [ensure_string_id(id) for id in incident_ids]
    
    results = {
        "status": "success",
        "linked_incidents": [],
        "comments_added": [],
        "problem_details": None
    }
    
    # Step 1: Get problem details
    try:
        problem_response = await make_api_request(f"problems/{problem_id_str}.json")
        
        if isinstance(problem_response, dict) and problem_response.get("error"):
            return json.dumps({
                "status": "failure",
                "message": f"Failed to retrieve problem details: {json.dumps(problem_response)}",
                "_system_message": f"Failed to retrieve details for problem #{problem_id_str}."
            }, indent=2)
            
        results["problem_details"] = problem_response
        problem_name = problem_response.get("name", f"Problem #{problem_id_str}")
        
        # Step 2: Link each incident to the problem
        for incident_id in incident_id_strs:
            try:
                # Update incident to link to problem
                link_data = {
                    "incident": {
                        "problem_id": problem_id_str
                    }
                }
                
                link_response = await make_api_request(
                    f"incidents/{incident_id}/json", 
                    method="PUT", 
                    data=link_data
                )
                
                if isinstance(link_response, dict) and link_response.get("error"):
                    results["status"] = "partial_failure"
                    results["linked_incidents"].append({
                        "incident_id": incident_id,
                        "status": "error",
                        "details": link_response
                    })
                else:
                    results["linked_incidents"].append({
                        "incident_id": incident_id,
                        "status": "success",
                        "details": link_response
                    })
                    
                    # Add comment if requested
                    if add_comments:
                        comment_data = {
                            "comment": {
                                "body": f"This incident has been linked to problem #{problem_id_str}: {problem_name}.",
                                "is_private": False
                            }
                        }
                        
                        comment_response = await make_api_request(
                            f"incidents/{incident_id}/comments.json", 
                            method="POST", 
                            data=comment_data
                        )
                        
                        if isinstance(comment_response, dict) and comment_response.get("error"):
                            results["comments_added"].append({
                                "incident_id": incident_id,
                                "status": "error",
                                "details": comment_response
                            })
                        else:
                            results["comments_added"].append({
                                "incident_id": incident_id,
                                "status": "success",
                                "details": comment_response
                            })
                
            except Exception as e:
                results["status"] = "partial_failure"
                results["linked_incidents"].append({
                    "incident_id": incident_id,
                    "status": "error",
                    "message": str(e)
                })
        
        # Add a user-friendly summary
        success_count = sum(1 for inc in results["linked_incidents"] if inc["status"] == "success")
        results["_system_message"] = f"Successfully linked {success_count} out of {len(incident_id_strs)} incidents to problem #{problem_id_str}."
        if results["status"] == "partial_failure":
            results["_system_message"] += " Some operations encountered issues. See details for more information."
            
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "failure",
            "message": f"Operation failed: {str(e)}",
            "_system_message": f"Failed to link incidents to problem #{problem_id_str}: {str(e)}"
        }, indent=2)

# Enhanced get_categories function with better structuring
@mcp.tool()
async def get_categories_structured() -> str:
    """Get a hierarchically structured list of all categories and subcategories."""
    response = await make_api_request("categories.json")
    
    # Check for errors
    if isinstance(response, dict) and response.get("error"):
        return json.dumps(response, indent=2)
    
    # Build category hierarchy
    category_map = {}
    root_categories = []
    
    # First, create a mapping of all categories
    for category in response:
        cat_id = category.get("id")
        if cat_id:
            category_map[cat_id] = {
                "id": cat_id,
                "name": category.get("name", "Unknown"),
                "parent_id": category.get("parent_id"),
                "children": []
            }
    
                # Then, build the hierarchy
    for cat_id, category in category_map.items():
        parent_id = category["parent_id"]
        if not parent_id:
            root_categories.append(category)
        elif parent_id in category_map:
            category_map[parent_id]["children"].append(category)
    
    structured_result = {
        "categories": root_categories,
        "total_count": len(response),
        "root_count": len(root_categories),
        "_system_message": f"Retrieved {len(response)} categories with {len(root_categories)} root categories."
    }
    
    return json.dumps(structured_result, indent=2)

# Enhanced search function with relevance ranking
@mcp.tool()
async def advanced_search_incidents(
    search_params: Dict[str, Any],
    max_results: int = 10,
    include_comments: bool = False,
    include_time_tracks: bool = False
) -> str:
    """
    Advanced incident search with rich parameters and relevance ranking.
    
    Args:
        search_params: Dictionary of search parameters (query, state, priority, dates, etc.)
        max_results: Maximum number of results to return
        include_comments: Whether to include comments in the results
        include_time_tracks: Whether to include time tracking entries
    """
    # Prepare parameters
    params = {}
    
    # Map search parameters to API parameters
    for key, value in search_params.items():
        if key == "query" and value:
            params["query"] = str(value)
        elif key == "state" and value:
            # Ensure valid state value
            valid_states = ["New", "Open", "In Progress", "Pending", "Resolved", "Closed"]
            corrected_state = fuzzy_match_parameter(str(value), valid_states)
            if corrected_state:
                params["state"] = corrected_state
            else:
                params["state"] = str(value)
        elif key == "priority" and value:
            # Ensure valid priority value
            valid_priorities = ["Low", "Medium", "High", "Critical"]
            corrected_priority = fuzzy_match_parameter(str(value), valid_priorities)
            if corrected_priority:
                params["priority"] = corrected_priority
            else:
                params["priority"] = str(value)
        elif key == "updated_since" and value:
            params["updated"] = str(value)
        elif key == "assignee_email" and value:
            params["assignee"] = str(value)
        elif key == "requester_email" and value:
            params["requester"] = str(value)
        elif key == "department_id" and value:
            params["department"] = ensure_string_id(value)
        elif key == "site_id" and value:
            params["site"] = ensure_string_id(value)
        elif key == "created_since" and value:
            params["created"] = str(value)
    
    # Set result limit
    params["per_page"] = str(min(max_results, 100))
    
    try:
        # Get incidents matching search criteria
        incidents_response = await make_api_request("incidents.json", params=params)
        
        # Check for errors
        if isinstance(incidents_response, dict) and incidents_response.get("error"):
            return json.dumps(incidents_response, indent=2)
        
        # Enhance each incident with additional data if requested
        enhanced_incidents = []
        
        for incident in incidents_response[:max_results]:
            incident_id = incident.get("id")
            enhanced_incident = dict(incident)
            
            if incident_id:
                # Add comments if requested
                if include_comments:
                    try:
                        comments = await make_api_request(f"incidents/{incident_id}/comments.json")
                        if not (isinstance(comments, dict) and comments.get("error")):
                            enhanced_incident["comments"] = comments
                    except Exception as e:
                        enhanced_incident["comments"] = {"error": str(e)}
                
                # Add time tracks if requested
                if include_time_tracks:
                    try:
                        time_tracks = await make_api_request(f"incidents/{incident_id}/time_tracks.json")
                        if not (isinstance(time_tracks, dict) and time_tracks.get("error")):
                            enhanced_incident["time_tracks"] = time_tracks
                    except Exception as e:
                        enhanced_incident["time_tracks"] = {"error": str(e)}
            
            enhanced_incidents.append(enhanced_incident)
        
        # Create a structured response with metadata
        result = {
            "results": enhanced_incidents,
            "count": len(enhanced_incidents),
            "search_params": search_params,
            "timestamp": datetime.datetime.now().isoformat(),
            "_system_message": f"Found {len(enhanced_incidents)} incidents matching your search criteria."
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": True,
            "message": f"Search failed: {str(e)}",
            "search_params": search_params,
            "_system_message": f"Failed to search for incidents: {str(e)}"
        }, indent=2)

# Enhanced tool for creating comprehensive knowledge base articles
@mcp.tool()
async def create_knowledge_article(
    title: str,
    content: str,
    category_id: Optional[int] = None,
    keywords: Optional[List[str]] = None,
    related_incidents: Optional[List[Union[str, int]]] = None,
    state: str = "Draft"
) -> str:
    """
    Create a comprehensive knowledge base article.
    
    Args:
        title: Title of the knowledge article
        content: Main content of the article
        category_id: Category to assign the article to
        keywords: List of keywords for improved searchability
        related_incidents: List of related incident IDs
        state: Publication state (Draft, Published, etc.)
    """
    # Prepare article data
    article_data = {
        "solution": {
            "title": title,
            "description": content,
            "state": state
        }
    }
    
    if category_id:
        article_data["solution"]["category_id"] = category_id
    
    if keywords and isinstance(keywords, list):
        # Join keywords into a comma-separated string
        article_data["solution"]["keywords"] = ",".join(keywords)
    
    try:
        # Create the knowledge article
        solution_response = await make_api_request(
            "solutions.json",
            method="POST",
            data=article_data
        )
        
        # Check for errors
        if isinstance(solution_response, dict) and solution_response.get("error"):
            return json.dumps(solution_response, indent=2)
        
        solution_id = solution_response.get("id")
        
        # Link related incidents if provided
        linked_incidents = []
        if solution_id and related_incidents:
            for incident_id in related_incidents:
                incident_id_str = ensure_string_id(incident_id)
                
                try:
                    # Add a comment to the incident with a link to the knowledge article
                    comment_data = {
                        "comment": {
                            "body": f"Related knowledge article created: \"{title}\" (ID: {solution_id})",
                            "is_private": False
                        }
                    }
                    
                    comment_response = await make_api_request(
                        f"incidents/{incident_id_str}/comments.json",
                        method="POST",
                        data=comment_data
                    )
                    
                    if isinstance(comment_response, dict) and comment_response.get("error"):
                        linked_incidents.append({
                            "incident_id": incident_id_str,
                            "status": "error",
                            "details": comment_response
                        })
                    else:
                        linked_incidents.append({
                            "incident_id": incident_id_str,
                            "status": "success",
                            "details": comment_response
                        })
                        
                except Exception as e:
                    linked_incidents.append({
                        "incident_id": incident_id_str,
                        "status": "error",
                        "message": str(e)
                    })
        
        # Prepare the final result
        result = {
            "solution": solution_response,
            "linked_incidents": linked_incidents,
            "_system_message": f"Knowledge article \"{title}\" created successfully with ID: {solution_id}."
        }
        
        if linked_incidents:
            success_count = sum(1 for inc in linked_incidents if inc["status"] == "success")
            result["_system_message"] += f" Linked to {success_count} out of {len(related_incidents)} incidents."
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": True,
            "message": f"Failed to create knowledge article: {str(e)}",
            "_system_message": f"Failed to create knowledge article \"{title}\": {str(e)}"
        }, indent=2)

# New function for getting detailed system status
@mcp.tool()
async def get_system_status() -> str:
    """Get a comprehensive system status report including incidents, users, and resources."""
    
    status_result = {
        "status": "success",
        "timestamp": datetime.datetime.now().isoformat(),
        "system_health": {
            "incidents": {
                "open_count": 0,
                "critical_count": 0,
                "resolved_last_24h": 0
            },
            "users": {
                "active_count": 0,
                "admin_count": 0
            },
            "resources": {
                "categories_count": 0,
                "departments_count": 0,
                "sites_count": 0,
                "knowledge_articles_count": 0
            }
        },
        "recent_activity": {
            "incidents": [],
            "comments": []
        },
        "_system_message": "System status report generated successfully."
    }
    
    try:
        # Get open incidents
        open_incidents = await make_api_request("incidents.json", params={"state": "Open,In Progress"})
        if not isinstance(open_incidents, dict) or not open_incidents.get("error"):
            status_result["system_health"]["incidents"]["open_count"] = len(open_incidents)
            # Count critical incidents
            status_result["system_health"]["incidents"]["critical_count"] = sum(
                1 for inc in open_incidents if inc.get("priority") == "Critical"
            )
            # Get recent incidents for activity
            if open_incidents:
                status_result["recent_activity"]["incidents"] = [
                    {
                        "id": inc.get("id"),
                        "name": inc.get("name"),
                        "priority": inc.get("priority"),
                        "state": inc.get("state"),
                        "created_at": inc.get("created_at")
                    }
                    for inc in sorted(
                        open_incidents, 
                        key=lambda x: x.get("created_at", ""), 
                        reverse=True
                    )[:5]
                ]
                
        # Get recently resolved incidents
        resolved_incidents = await make_api_request(
            "incidents.json", 
            params={"state": "Resolved", "updated": "1d"}
        )
        if not isinstance(resolved_incidents, dict) or not resolved_incidents.get("error"):
            status_result["system_health"]["incidents"]["resolved_last_24h"] = len(resolved_incidents)
        
        # Get users
        users = await make_api_request("users.json")
        if not isinstance(users, dict) or not users.get("error"):
            status_result["system_health"]["users"]["active_count"] = len(users)
            # Count admin users
            status_result["system_health"]["users"]["admin_count"] = sum(
                1 for user in users 
                if user.get("role", {}).get("name", "").lower() == "admin"
            )
            
        # Get resource counts
        categories = await make_api_request("categories.json")
        if not isinstance(categories, dict) or not categories.get("error"):
            status_result["system_health"]["resources"]["categories_count"] = len(categories)
            
        departments = await make_api_request("departments.json")
        if not isinstance(departments, dict) or not departments.get("error"):
            status_result["system_health"]["resources"]["departments_count"] = len(departments)
            
        sites = await make_api_request("sites.json")
        if not isinstance(sites, dict) or not sites.get("error"):
            status_result["system_health"]["resources"]["sites_count"] = len(sites)
            
        solutions = await make_api_request("solutions.json")
        if not isinstance(solutions, dict) or not solutions.get("error"):
            status_result["system_health"]["resources"]["knowledge_articles_count"] = len(solutions)
        
        # Set overall status message
        status_result["_system_message"] = (
            f"System Status: {status_result['system_health']['incidents']['open_count']} open incidents "
            f"({status_result['system_health']['incidents']['critical_count']} critical). "
            f"{status_result['system_health']['incidents']['resolved_last_24h']} incidents resolved in the last 24 hours."
        )
        
        return json.dumps(status_result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to generate system status: {str(e)}",
            "_system_message": f"Failed to generate system status report: {str(e)}"
        }, indent=2)

# New function for bulk operations
@mcp.tool()
async def bulk_update_incidents(
    incident_ids: List[Union[str, int]],
    updates: Dict[str, Any]
) -> str:
    """
    Update multiple incidents with the same changes in bulk.
    
    Args:
        incident_ids: List of incident IDs to update
        updates: Dictionary of field updates to apply to all incidents
    """
    results = {
        "status": "success",
        "updated_incidents": [],
        "failed_updates": [],
        "update_count": 0,
        "failure_count": 0,
        "_system_message": ""
    }
    
    # Prepare the update payload template
    data_template = {"incident": {}}
    
    # Map updates to API fields
    for key, value in updates.items():
        if key in ["name", "description", "priority", "state", "due_at"]:
            # Direct field mapping
            data_template["incident"][key] = value
        elif key == "assignee_email":
            # Handle assignee update
            data_template["incident"]["assignee"] = {"email": value}
        elif key == "requester_email":
            # Handle requester update
            data_template["incident"]["requester"] = {"email": value}
        elif key == "department_id":
            # Handle department update
            data_template["incident"]["department_id"] = value
        elif key == "site_id":
            # Handle site update
            data_template["incident"]["site_id"] = value
        elif key == "category_id":
            # Handle category update
            data_template["incident"]["category_id"] = value
        elif key == "subcategory_id":
            # Handle subcategory update
            data_template["incident"]["subcategory_id"] = value
    
    # Apply normalization for common fields
    if "state" in data_template["incident"]:
        valid_states = ["New", "Open", "In Progress", "Pending", "Resolved", "Closed"]
        state_value = data_template["incident"]["state"]
        corrected_state = fuzzy_match_parameter(state_value, valid_states)
        if corrected_state and corrected_state != state_value:
            logger.info(f"Corrected state value from '{state_value}' to '{corrected_state}'")
            data_template["incident"]["state"] = corrected_state
    
    if "priority" in data_template["incident"]:
        valid_priorities = ["Low", "Medium", "High", "Critical"]
        priority_value = data_template["incident"]["priority"]
        corrected_priority = fuzzy_match_parameter(priority_value, valid_priorities)
        if corrected_priority and corrected_priority != priority_value:
            logger.info(f"Corrected priority value from '{priority_value}' to '{corrected_priority}'")
            data_template["incident"]["priority"] = corrected_priority
    
    # Process each incident
    for incident_id in incident_ids:
        incident_id_str = ensure_string_id(incident_id)
        
        try:
            # Make a copy of the template data
            update_data = json.loads(json.dumps(data_template))
            
            # Update the incident
            response = await make_api_request(
                f"incidents/{incident_id_str}.json",
                method="PUT",
                data=update_data
            )
            
            if isinstance(response, dict) and response.get("error"):
                results["status"] = "partial_failure"
                results["failed_updates"].append({
                    "incident_id": incident_id_str,
                    "error": response
                })
                results["failure_count"] += 1
            else:
                results["updated_incidents"].append({
                    "incident_id": incident_id_str,
                    "details": response
                })
                results["update_count"] += 1
                
        except Exception as e:
            results["status"] = "partial_failure"
            results["failed_updates"].append({
                "incident_id": incident_id_str,
                "error": str(e)
            })
            results["failure_count"] += 1
    
    # Generate system message
    if results["status"] == "success":
        results["_system_message"] = f"Successfully updated all {len(incident_ids)} incidents."
    else:
        results["_system_message"] = (
            f"Updated {results['update_count']} out of {len(incident_ids)} incidents. "
            f"{results['failure_count']} updates failed."
        )
    
    return json.dumps(results, indent=2)

if __name__ == "__main__":  # Double underscores  # Note the underscores    # Initialize and run the server
    mcp.run(transport='stdio')