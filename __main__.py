"""
SolarWinds Service Desk MCP Server - Main entry point

This server provides MCP tools for interacting with the
SolarWinds Service Desk API (formerly Samanage API).
"""
from solarwinds_mcp_server.server import mcp

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')