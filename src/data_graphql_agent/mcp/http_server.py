"""MCP HTTP server implementation."""

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from .config import load_config
from .tools import get_tools
from .handlers import handle_tool_call

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_http_app() -> FastAPI:
    """Create FastAPI application for HTTP transport.

    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="Data GraphQL Agent MCP Server",
        description="MCP server that generates Apollo GraphQL servers from BigQuery queries",
        version="0.1.0",
    )

    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint.

        Returns:
            Health status
        """
        return {
            "status": "healthy",
            "service": "data-graphql-agent",
            "transport": "http",
        }

    @app.get("/")
    async def root(request: Request) -> Any:
        """Root endpoint - returns service info or SSE stream.

        Args:
            request: FastAPI request object

        Returns:
            Service info or SSE stream
        """
        accept_header = request.headers.get("accept", "")

        if "text/event-stream" in accept_header:
            # Return SSE stream
            async def event_stream():
                yield "event: message\n"
                yield 'data: {"type": "connected", "service": "data-graphql-agent"}\n\n'

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
            )

        # Return service info
        return {
            "service": "data-graphql-agent",
            "description": "MCP server for generating Apollo GraphQL servers",
            "version": "0.1.0",
            "transport": "http",
            "endpoints": {
                "health": "/health",
                "tools": "/mcp/tools",
                "call_tool": "/mcp/call-tool",
            },
        }

    @app.get("/mcp/tools")
    async def list_tools() -> Dict[str, Any]:
        """List available MCP tools.

        Returns:
            List of tool definitions
        """
        tools = get_tools()
        return {"tools": tools}

    @app.post("/mcp/call-tool")
    async def call_tool(request: Request) -> JSONResponse:
        """Execute an MCP tool via JSON-RPC.

        Args:
            request: FastAPI request object

        Returns:
            Tool execution results
        """
        try:
            body = await request.json()
            tool_name = body.get("name")
            arguments = body.get("arguments", {})

            if not tool_name:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32600,
                            "message": "Invalid request - missing tool name",
                        },
                        "id": body.get("id"),
                    },
                )

            logger.info(f"Executing tool via HTTP: {tool_name}")
            result = await handle_tool_call(tool_name, arguments)

            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": body.get("id", 1),
                }
            )

        except Exception as e:
            logger.error(f"Error executing tool: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}",
                    },
                    "id": body.get("id") if "body" in locals() else None,
                },
            )

    return app


def run_http_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run HTTP server.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    logger.info(f"Starting Data GraphQL Agent HTTP server on {host}:{port}")

    app = create_http_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    config = load_config()
    run_http_server(host=config.mcp_host, port=config.mcp_port)

