"""Configuration management for MCP server."""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class MCPConfig(BaseModel):
    """Configuration for MCP server."""

    # GCP Configuration
    gcp_project_id: str = Field(
        default_factory=lambda: os.getenv("GCP_PROJECT_ID", ""),
        description="Google Cloud Project ID",
    )
    gcp_location: str = Field(
        default_factory=lambda: os.getenv("GCP_LOCATION", "us-central1"),
        description="Google Cloud Location",
    )

    # Output Configuration
    graphql_output_dir: str = Field(
        default_factory=lambda: os.getenv("GRAPHQL_OUTPUT_DIR", "./output"),
        description="Output directory for generated GraphQL server code",
    )

    # MCP Server Configuration
    mcp_transport: str = Field(
        default_factory=lambda: os.getenv("MCP_TRANSPORT", "stdio"),
        description="MCP transport type (stdio or http)",
    )
    mcp_host: str = Field(
        default_factory=lambda: os.getenv("MCP_HOST", "0.0.0.0"),
        description="MCP HTTP server host",
    )
    mcp_port: int = Field(
        default_factory=lambda: int(os.getenv("MCP_PORT", "8080")),
        description="MCP HTTP server port",
    )

    # Authentication Configuration
    mcp_auth_enabled: bool = Field(
        default_factory=lambda: os.getenv("MCP_AUTH_ENABLED", "false").lower()
        == "true",
        description="Enable MCP authentication",
    )

    def validate_required_fields(self) -> None:
        """Validate that required configuration fields are set."""
        if not self.gcp_project_id:
            raise ValueError("GCP_PROJECT_ID environment variable is required")


def load_config() -> MCPConfig:
    """Load and validate configuration from environment variables.

    Returns:
        MCPConfig: Validated configuration object

    Raises:
        ValueError: If required configuration is missing
    """
    config = MCPConfig()
    config.validate_required_fields()
    return config

