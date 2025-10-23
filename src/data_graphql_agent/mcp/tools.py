"""MCP tool definitions for Data GraphQL Agent."""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get list of MCP tool definitions.

    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "name": "generate_graphql_api",
            "description": "Generate a complete Apollo GraphQL Server from BigQuery SQL queries. "
            "Creates TypeScript code with resolvers, schema, lineage tracking, "
            "Docker configuration, and test client.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "description": "List of BigQuery queries to convert to GraphQL API",
                        "items": {
                            "type": "object",
                            "properties": {
                                "queryName": {
                                    "type": "string",
                                    "description": "CamelCase name for the GraphQL query (e.g., trendingItemsByRegion)",
                                },
                                "sql": {
                                    "type": "string",
                                    "description": "Validated BigQuery SQL query string",
                                },
                                "source_tables": {
                                    "type": "array",
                                    "description": "Fully qualified BigQuery table names (project.dataset.table)",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["queryName", "sql", "source_tables"],
                        },
                        "minItems": 1,
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name of the project (used for lineage target naming)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for generated code (gs://, file://, or absolute path). "
                        "If not provided, uses GRAPHQL_OUTPUT_DIR environment variable.",
                    },
                    "validation_level": {
                        "type": "string",
                        "enum": ["quick", "standard", "full"],
                        "description": "Validation thoroughness: quick (~1s), standard (~10s), full (~60s). Default: standard",
                    },
                    "auto_fix": {
                        "type": "boolean",
                        "description": "Attempt to automatically fix validation errors. Default: false",
                    },
                },
                "required": ["queries", "project_name"],
            },
        },
        {
            "name": "validate_graphql_schema",
            "description": "Validate a GraphQL schema file for syntax and type errors.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "schema_path": {
                        "type": "string",
                        "description": "Path to GraphQL schema file to validate",
                    }
                },
                "required": ["schema_path"],
            },
        },
    ]

