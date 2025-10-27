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
            "Creates TypeScript code with resolvers, schema, Docker configuration, and test client. "
            "Supports rich documentation from query generation metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "description": "List of BigQuery queries to convert to GraphQL API",
                        "items": {
                            "type": "object",
                            "properties": {
                                "query_name": {
                                    "type": "string",
                                    "description": "Unique query identifier in snake_case or camelCase (e.g., trending_items_by_region or trendingItemsByRegion)",
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
                                "description": {
                                    "type": "string",
                                    "description": "Human-readable description of what the query does (appears in GraphQL schema)",
                                },
                                "alignment_score": {
                                    "type": "number",
                                    "description": "Alignment score from query generation (0.0-1.0, appears in schema documentation)",
                                },
                                "iterations": {
                                    "type": "integer",
                                    "description": "Number of refinement iterations during generation (appears in schema documentation)",
                                },
                                "generation_time_ms": {
                                    "type": "number",
                                    "description": "Time taken to generate this query in milliseconds (appears in schema documentation)",
                                },
                            },
                            "required": ["query_name", "sql", "source_tables"],
                        },
                        "minItems": 1,
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name of the project (used for API naming and documentation)",
                    },
                    "insight": {
                        "type": "string",
                        "description": "High-level insight or purpose of the API (appears in GraphQL Query type description)",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of the query generation process with stats (used for API-level documentation)",
                    },
                    "dataset_count": {
                        "type": "integer",
                        "description": "Number of datasets analyzed during query generation (appears in schema documentation)",
                    },
                    "execution_time_ms": {
                        "type": "number",
                        "description": "Total execution time for query generation in milliseconds (appears in schema documentation)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Base output directory for generated code (gs://, file://, or absolute path). "
                        "Code will be written to: <output_path>/<project_name>/graphql_<timestamp>/. "
                        "Project names are converted to lowercase for case-insensitive folder names. "
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

