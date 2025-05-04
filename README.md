# SolarWinds Service Desk MCP Server

This Model Context Protocol (MCP) server allows integration with the SolarWinds Service Desk API (formerly Samanage API). It exposes API endpoints as resources and provides tools for interacting with various entities like incidents, problems, and users.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/solarwinds-mcp-server.git
   cd solarwinds-mcp-server
   ```

2. **Create and activate a virtual environment:**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the package:**
   ```bash
   uv pip install -e .
   ```

4. **Create a .env file with your API credentials:**
   ```
   SOLARWINDS_API_TOKEN=your_api_token_here
   SOLARWINDS_API_URL=https://api.samanage.com
   # For European based customers use: https://apieu.samanage.com
   # For APJ based customers use: https://apiau.samanage.com
   ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Required for Claude features
   ```

## Usage

### Running the server

You can run the MCP server directly:
```bash
uv run python -m src
```

Or use the MCP CLI:
```bash
uv run mcp dev src
```

### Running the chatbot with web interface

For a complete experience with a web interface, you can use the provided scripts:

#### Method 1: Quick Start Script

```bash
# Make the script executable (first time only)
chmod +x start_server.sh

# Run the server and web interface
./start_server.sh
```

#### Method 2: Python Script

```bash
# Install dependencies first
uv pip install -e .

# Run the chatbot
python run_chatbot.py
```

This will:
1. Start the MCP server in the background
2. Start the Flask web interface
3. Open a browser window to access the chatbot

You can customize the host and port:
```bash
python run_chatbot.py --host 0.0.0.0 --port 8080
```

For debugging:
```bash
python run_chatbot.py --debug
```

### Using with Claude Desktop

Create a config file at the appropriate location for your OS:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following configuration:
```json
{
  "mcpServers": {
    "solarwinds": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/solarwinds-mcp-server",
        "run",
        "python",
        "-m",
        "src"
      ],
      "env": {
        "SOLARWINDS_API_TOKEN": "your_api_token_here",
        "SOLARWINDS_API_URL": "https://api.samanage.com"
      }
    }
  }
}
```

Restart Claude Desktop.

## Testing the System

### Testing the MCP server and tools

```bash
# Test the MCP server tools
python test_tools.py
```

### Testing the web interface utilities

```bash
# Test the web interface components
python test_web.py
```

## Troubleshooting

### Server keeps terminating
If the MCP server terminates unexpectedly, check the logs in:
- `mcp_server.log` - For MCP server logs
- `solarwinds_mcp_server.log` - For more detailed server logs
- `solarwinds_client.log` - For client connection logs
- `chatbot.log` - For overall system logs

### API Authentication Issues
If you see 406 Not Acceptable errors, check that:
- Your API token is correctly set in the .env file
- You're using the correct API URL for your region

### Demo Mode
When using the test_token value, the system runs in simulation mode with mock data.

## Available Resources

- `samanage://api` - List of all available API endpoints
- `samanage://incidents` - List of all incidents
- `samanage://incidents/{id}` - Details of a specific incident
- `samanage://problems` - List of all problems
- `samanage://problems/{id}` - Details of a specific problem
- `samanage://changes` - List of all changes
- `samanage://changes/{id}` - Details of a specific change
- `samanage://users` - List of all users
- `samanage://users/{id}` - Details of a specific user
- `samanage://departments` - List of all departments
- `samanage://departments/{id}` - Details of a specific department
- `samanage://sites` - List of all sites
- `samanage://sites/{id}` - Details of a specific site
- `samanage://groups` - List of all groups
- `samanage://groups/{id}` - Details of a specific group
- `samanage://roles` - List of all roles
- `samanage://roles/{id}` - Details of a specific role
- `samanage://categories` - List of all categories
- `samanage://categories/{id}` - Details of a specific category
- `samanage://solutions` - List of all solutions
- `samanage://solutions/{id}` - Details of a specific solution

## Available Tools

### Incident Management
- `create_incident` - Create a new incident
- `get_incident` - Get incident details
- `update_incident` - Update an existing incident
- `delete_incident` - Delete an incident
- `list_incidents` - List incidents with various filters
- `add_comment_to_incident` - Add a comment to an incident

### Problem Management
- `create_problem` - Create a new problem
- `get_problem` - Get problem details
- `update_problem` - Update an existing problem
- `delete_problem` - Delete a problem
- `list_problems` - List problems with various filters
- `link_incidents_to_problem` - Link incidents to a problem

### Change Management
- `create_change` - Create a new change
- `get_change` - Get change details
- `update_change` - Update an existing change
- `delete_change` - Delete a change
- `list_changes` - List changes with various filters

### User and Organization Management
- `get_user` - Get user details
- `get_user_by_email` - Find a user by email
- `list_users` - List users with various filters
- `create_department` - Create a new department
- `get_department` - Get department details
- `update_department` - Update an existing department
- `delete_department` - Delete a department
- `list_departments` - List departments with various filters

### Knowledge Management
- `create_category` - Create a new category

### Claude Integration
- `cache_prompt` - Cache a prompt with Claude API
- `list_cached_prompts` - List all cached prompts
- `use_cached_prompt` - Use a previously cached prompt
- `delete_cached_prompt` - Delete a cached prompt
- `batch_process_messages` - Process multiple messages in a batch
- `analyze_with_claude` - Analyze data using Claude

## Development

The project is structured as follows:

- `src/` - Core MCP server code
  - `api_helpers.py` - Helper functions for the SolarWinds API
  - `incident_tools.py` - Incident management functions
  - `problem_tools.py` - Problem management functions
  - `change_tools.py` - Change management functions
  - `user_tools.py` - User management functions
  - `organization_tools.py` - Department, site, group, role management
  - `knowledge_tools.py` - Category and solution management
- `flask_app/` - Web interface
  - `app.py` - Flask application
  - `static/` - Static assets
  - `templates/` - HTML templates
  - `utils/` - Utility functions

## License

[MIT License](LICENSE)