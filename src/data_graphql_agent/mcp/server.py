"""MCP server implementation with stdio transport."""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import load_config
from .tools import get_tools
from .handlers import handle_tool_call

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create MCP server instance
app = Server("data-graphql-agent")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools.

    Returns:
        List of tool definitions
    """
    tools_config = get_tools()
    return [
        Tool(
            name=tool["name"],
            description=tool["description"],
            inputSchema=tool["inputSchema"],
        )
        for tool in tools_config
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of text content results
    """
    try:
        logger.info(f"Executing tool: {name}")
        result = await handle_tool_call(name, arguments)

        return [
            TextContent(
                type="text",
                text=str(result),
            )
        ]
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=f"Error: {str(e)}",
            )
        ]


async def main() -> None:
    """Main entry point for stdio transport."""
    logger.info("Starting Data GraphQL Agent MCP server (stdio)")

    # Load and validate configuration
    try:
        config = load_config()
        logger.info(f"Configuration loaded successfully")
        logger.info(f"  Project: {config.gcp_project_id}")
        logger.info(f"  Output: {config.graphql_output_dir}")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise

    # Run stdio server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


def run_server() -> None:
    """Run the MCP server.

    Chooses transport based on MCP_TRANSPORT environment variable.
    """
    config = load_config()

    if config.mcp_transport.lower() == "http":
        from .http_server import run_http_server

        logger.info("Starting HTTP transport")
        run_http_server(host=config.mcp_host, port=config.mcp_port)
    else:
        logger.info("Starting stdio transport")
        asyncio.run(main())


if __name__ == "__main__":
    run_server()

