"""Request models for MCP tool inputs."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class QueryInput(BaseModel):
    """Input model for a single BigQuery query to convert to GraphQL."""

    query_name: str = Field(
        ...,
        description="CamelCase name for the GraphQL query (e.g., trendingItemsByRegion)",
    )
    sql: str = Field(..., description="Validated BigQuery SQL query string")
    source_tables: List[str] = Field(
        ...,
        description="Fully qualified BigQuery table names (e.g., project.dataset.table)",
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description of what the query does and its approach",
    )
    alignment_score: Optional[float] = Field(
        None,
        description="Alignment score from query generation (0.0-1.0)",
    )
    iterations: Optional[int] = Field(
        None,
        description="Number of refinement iterations during generation",
    )
    generation_time_ms: Optional[float] = Field(
        None,
        description="Time taken to generate this query in milliseconds",
    )
    validation_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Validation details including result_schema with field descriptions",
    )

    @field_validator("query_name")
    @classmethod
    def validate_query_name(cls, v: str) -> str:
        """Validate that query name is a valid GraphQL field name."""
        if not v:
            raise ValueError("query_name cannot be empty")
        if not v[0].islower():
            raise ValueError("query_name must start with lowercase letter (camelCase)")
        if not v.replace("_", "").isalnum():
            raise ValueError("query_name must be alphanumeric (underscores allowed)")
        return v

    @field_validator("sql")
    @classmethod
    def validate_sql(cls, v: str) -> str:
        """Validate SQL is not empty."""
        if not v or not v.strip():
            raise ValueError("sql cannot be empty")
        return v.strip()

    @field_validator("source_tables")
    @classmethod
    def validate_source_tables(cls, v: List[str]) -> List[str]:
        """Validate source tables are properly formatted."""
        if not v:
            raise ValueError("source_tables cannot be empty")
        for table in v:
            parts = table.split(".")
            if len(parts) != 3:
                raise ValueError(
                    f"Invalid table format: {table}. Expected format: project.dataset.table"
                )
        return v


class GenerateGraphQLRequest(BaseModel):
    """Request model for generate_graphql_api tool."""

    queries: List[QueryInput] = Field(
        ..., description="List of queries to convert to GraphQL API"
    )
    project_name: str = Field(
        ..., description="Name of the project (used for API naming and documentation)"
    )
    output_path: Optional[str] = Field(
        None,
        description="Output path for generated code (gs://, file://, or absolute path). "
        "If not provided, uses GRAPHQL_OUTPUT_DIR environment variable.",
    )
    insight: Optional[str] = Field(
        None,
        description="High-level insight or purpose of the API from query generation",
    )
    summary: Optional[str] = Field(
        None,
        description="Summary of the query generation process including stats and context",
    )
    dataset_count: Optional[int] = Field(
        None,
        description="Number of datasets analyzed during query generation",
    )
    execution_time_ms: Optional[float] = Field(
        None,
        description="Total execution time for query generation in milliseconds",
    )

    @field_validator("queries")
    @classmethod
    def validate_queries(cls, v: List[QueryInput]) -> List[QueryInput]:
        """Validate that queries list is not empty."""
        if not v:
            raise ValueError("queries list cannot be empty")
        return v

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        """Validate project name."""
        if not v or not v.strip():
            raise ValueError("project_name cannot be empty")
        return v.strip()


class ValidateSchemaRequest(BaseModel):
    """Request model for validate_graphql_schema tool."""

    schema_path: str = Field(..., description="Path to GraphQL schema file to validate")

