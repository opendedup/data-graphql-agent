"""Integration tests for MCP tools."""

from typing import TYPE_CHECKING
import pytest
import os
from pathlib import Path

from data_graphql_agent.mcp.handlers import (
    handle_generate_graphql_api,
    handle_validate_graphql_schema,
)

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


@pytest.mark.asyncio
async def test_generate_graphql_api_integration(
    mocker: "MockerFixture", tmp_path: Path
) -> None:
    """Test end-to-end GraphQL API generation.

    Args:
        mocker: Pytest mocker fixture
        tmp_path: Temporary directory fixture
    """
    # Mock BigQuery client
    mock_schema = [
        mocker.Mock(
            name="id",
            field_type="INT64",
            mode="REQUIRED",
            fields=None,
        ),
        mocker.Mock(
            name="name",
            field_type="STRING",
            mode="NULLABLE",
            fields=None,
        ),
    ]

    mock_job = mocker.Mock()
    mock_job.schema = mock_schema

    mocker.patch(
        "data_graphql_agent.generation.schema_generator.bigquery.Client"
    )
    mocker.patch(
        "data_graphql_agent.generation.schema_generator.SchemaGenerator._get_query_schema",
        return_value=mock_schema,
    )

    # Prepare request
    arguments = {
        "queries": [
            {
                "queryName": "testQuery",
                "sql": "SELECT id, name FROM `project.dataset.table`",
                "source_tables": ["project.dataset.table"],
            }
        ],
        "project_name": "test-project",
        "output_path": str(tmp_path),
    }

    # Execute tool
    result = await handle_generate_graphql_api(arguments)

    # Verify response
    assert result["success"] is True
    assert "test-project" in result["message"]
    assert len(result["files_generated"]) > 0

    # Verify files were created
    assert (tmp_path / "package.json").exists()
    assert (tmp_path / "tsconfig.json").exists()
    assert (tmp_path / "Dockerfile").exists()
    assert (tmp_path / "src" / "server.ts").exists()
    assert (tmp_path / "src" / "typeDefs.ts").exists()
    assert (tmp_path / "src" / "resolvers.ts").exists()


@pytest.mark.asyncio
async def test_validate_schema_valid(tmp_path: Path) -> None:
    """Test schema validation with valid schema.

    Args:
        tmp_path: Temporary directory fixture
    """
    # Create valid schema file
    schema_path = tmp_path / "schema.graphql"
    schema_path.write_text(
        """
        type Query {
            testQuery: String
        }
        """
    )

    # Execute tool
    arguments = {"schema_path": str(schema_path)}
    result = await handle_validate_graphql_schema(arguments)

    # Verify response
    assert result["valid"] is True
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_validate_schema_invalid(tmp_path: Path) -> None:
    """Test schema validation with invalid schema.

    Args:
        tmp_path: Temporary directory fixture
    """
    # Create invalid schema file (missing Query type)
    schema_path = tmp_path / "schema.graphql"
    schema_path.write_text(
        """
        type User {
            id: Int
            name: String
        }
        """
    )

    # Execute tool
    arguments = {"schema_path": str(schema_path)}
    result = await handle_validate_graphql_schema(arguments)

    # Verify response
    assert result["valid"] is False
    assert len(result["errors"]) > 0
    assert any("Query" in error for error in result["errors"])


@pytest.mark.asyncio
async def test_validate_schema_file_not_found() -> None:
    """Test schema validation with non-existent file."""
    # Execute tool with non-existent path
    arguments = {"schema_path": "/nonexistent/schema.graphql"}
    result = await handle_validate_graphql_schema(arguments)

    # Verify response
    assert result["valid"] is False
    assert len(result["errors"]) > 0
    assert "not found" in result["errors"][0].lower()

