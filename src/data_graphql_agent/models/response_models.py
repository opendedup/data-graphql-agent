"""Response models for MCP tool outputs."""

from typing import List, Optional
from pydantic import BaseModel, Field


class FileManifest(BaseModel):
    """Manifest of a generated file."""

    path: str = Field(..., description="Relative path of the file")
    size_bytes: int = Field(..., description="Size of the file in bytes")
    description: str = Field(..., description="Description of the file's purpose")


class GenerateGraphQLResponse(BaseModel):
    """Response model for generate_graphql_api tool."""

    success: bool = Field(..., description="Whether generation was successful")
    output_path: str = Field(..., description="Path where files were generated")
    files_generated: List[FileManifest] = Field(
        ..., description="List of generated files"
    )
    message: str = Field(..., description="Summary message")
    error: Optional[str] = Field(None, description="Error message if generation failed")


class ValidateSchemaResponse(BaseModel):
    """Response model for validate_graphql_schema tool."""

    valid: bool = Field(..., description="Whether the schema is valid")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(
        default_factory=list, description="List of validation warnings"
    )
    message: str = Field(..., description="Summary message")

