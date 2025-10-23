"""Test request and response models."""

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from data_graphql_agent.models.request_models import (
    QueryInput,
    GenerateGraphQLRequest,
    ValidateSchemaRequest,
)
from data_graphql_agent.models.response_models import (
    FileManifest,
    GenerateGraphQLResponse,
    ValidateSchemaResponse,
)

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


def test_query_input_valid() -> None:
    """Test QueryInput with valid data."""
    query = QueryInput(
        query_name="trendingItems",
        sql="SELECT * FROM `project.dataset.table`",
        source_tables=["project.dataset.table"],
    )

    assert query.query_name == "trendingItems"
    assert query.sql == "SELECT * FROM `project.dataset.table`"
    assert len(query.source_tables) == 1


def test_query_input_invalid_name() -> None:
    """Test QueryInput with invalid query name."""
    with pytest.raises(ValidationError) as exc_info:
        QueryInput(
            query_name="InvalidName",  # Should start with lowercase
            sql="SELECT * FROM table",
            source_tables=["project.dataset.table"],
        )

    assert "query_name must start with lowercase" in str(exc_info.value)


def test_query_input_invalid_table_format() -> None:
    """Test QueryInput with invalid table format."""
    with pytest.raises(ValidationError) as exc_info:
        QueryInput(
            query_name="validName",
            sql="SELECT * FROM table",
            source_tables=["invalid_table"],  # Missing project and dataset
        )

    assert "Invalid table format" in str(exc_info.value)


def test_generate_graphql_request_valid() -> None:
    """Test GenerateGraphQLRequest with valid data."""
    request = GenerateGraphQLRequest(
        queries=[
            QueryInput(
                query_name="query1",
                sql="SELECT * FROM `project.dataset.table1`",
                source_tables=["project.dataset.table1"],
            )
        ],
        project_name="test-project",
        output_path="gs://bucket/path",
    )

    assert len(request.queries) == 1
    assert request.project_name == "test-project"
    assert request.output_path == "gs://bucket/path"


def test_generate_graphql_request_empty_queries() -> None:
    """Test GenerateGraphQLRequest with empty queries list."""
    with pytest.raises(ValidationError) as exc_info:
        GenerateGraphQLRequest(
            queries=[],
            project_name="test-project",
        )

    assert "queries list cannot be empty" in str(exc_info.value)


def test_file_manifest() -> None:
    """Test FileManifest model."""
    manifest = FileManifest(
        path="/path/to/file.ts",
        size_bytes=1024,
        description="TypeScript file",
    )

    assert manifest.path == "/path/to/file.ts"
    assert manifest.size_bytes == 1024
    assert manifest.description == "TypeScript file"


def test_generate_graphql_response_success() -> None:
    """Test GenerateGraphQLResponse for successful generation."""
    response = GenerateGraphQLResponse(
        success=True,
        output_path="gs://bucket/output",
        files_generated=[
            FileManifest(
                path="package.json",
                size_bytes=500,
                description="Package config",
            )
        ],
        message="Generation successful",
    )

    assert response.success is True
    assert response.output_path == "gs://bucket/output"
    assert len(response.files_generated) == 1
    assert response.error is None


def test_generate_graphql_response_failure() -> None:
    """Test GenerateGraphQLResponse for failed generation."""
    response = GenerateGraphQLResponse(
        success=False,
        output_path="",
        files_generated=[],
        message="Generation failed",
        error="Invalid SQL query",
    )

    assert response.success is False
    assert response.error == "Invalid SQL query"


def test_validate_schema_response_valid() -> None:
    """Test ValidateSchemaResponse for valid schema."""
    response = ValidateSchemaResponse(
        valid=True,
        errors=[],
        warnings=["Minor formatting issue"],
        message="Schema is valid",
    )

    assert response.valid is True
    assert len(response.errors) == 0
    assert len(response.warnings) == 1


def test_validate_schema_response_invalid() -> None:
    """Test ValidateSchemaResponse for invalid schema."""
    response = ValidateSchemaResponse(
        valid=False,
        errors=["Missing Query type", "Invalid syntax"],
        warnings=[],
        message="Schema has errors",
    )

    assert response.valid is False
    assert len(response.errors) == 2

