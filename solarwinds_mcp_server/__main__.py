from solarwinds_mcp_server.server import mcp

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')