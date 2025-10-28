"""Test project generator."""

from typing import TYPE_CHECKING

import pytest

from data_graphql_agent.generation.project_generator import ProjectGenerator
from data_graphql_agent.models.request_models import QueryInput

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def project_generator(mocker: "MockerFixture") -> ProjectGenerator:
    """Create project generator fixture.

    Args:
        mocker: Pytest mocker fixture

    Returns:
        ProjectGenerator instance with mocked BigQuery client
    """
    mocker.patch("google.cloud.bigquery.Client")
    return ProjectGenerator(
        project_id="test-project-123",
        gcp_location="us-central1"
    )


def test_init_with_default_location(mocker: "MockerFixture") -> None:
    """Test ProjectGenerator initialization with default location.

    Args:
        mocker: Pytest mocker fixture
    """
    mocker.patch("google.cloud.bigquery.Client")
    generator = ProjectGenerator(project_id="test-project")
    
    assert generator.project_id == "test-project"
    assert generator.gcp_location == "US"


def test_init_with_custom_location(mocker: "MockerFixture") -> None:
    """Test ProjectGenerator initialization with custom location.

    Args:
        mocker: Pytest mocker fixture
    """
    mocker.patch("google.cloud.bigquery.Client")
    generator = ProjectGenerator(
        project_id="test-project",
        gcp_location="europe-west1"
    )
    
    assert generator.project_id == "test-project"
    assert generator.gcp_location == "europe-west1"


def test_generate_env_example(project_generator: ProjectGenerator) -> None:
    """Test .env.example file generation with actual values.

    Args:
        project_generator: ProjectGenerator fixture
    """
    env_example = project_generator._generate_env_example()
    
    assert "BIGQUERY_PROJECT_ID=test-project-123" in env_example
    assert "BIGQUERY_LOCATION=us-central1" in env_example
    assert "PORT=4000" in env_example
    assert "NODE_ENV=development" in env_example


def test_generate_env_file(project_generator: ProjectGenerator) -> None:
    """Test .env file generation with actual values.

    Args:
        project_generator: ProjectGenerator fixture
    """
    env_file = project_generator._generate_env_file()
    
    assert "BIGQUERY_PROJECT_ID=test-project-123" in env_file
    assert "BIGQUERY_LOCATION=us-central1" in env_file
    assert "PORT=4000" in env_file
    assert "NODE_ENV=development" in env_file


def test_generate_project_includes_env_files(
    project_generator: ProjectGenerator,
    mocker: "MockerFixture"
) -> None:
    """Test that generate_project includes both .env and .env.example.

    Args:
        project_generator: ProjectGenerator fixture
        mocker: Pytest mocker fixture
    """
    # Mock the schema generator
    mocker.patch.object(
        project_generator.schema_generator,
        "generate_schema_from_queries",
        return_value=("type Query { test: String }", {})
    )
    
    queries = [
        QueryInput(
            query_name="testQuery",
            sql="SELECT * FROM `project.dataset.table`",
            source_tables=["project.dataset.table"]
        )
    ]
    
    files = project_generator.generate_project(
        project_name="Test Project",
        queries=queries
    )
    
    # Check that both env files are generated
    assert ".env.example" in files
    assert ".env" in files
    
    # Verify they contain the correct values
    assert "BIGQUERY_PROJECT_ID=test-project-123" in files[".env.example"]
    assert "BIGQUERY_LOCATION=us-central1" in files[".env.example"]
    assert "BIGQUERY_PROJECT_ID=test-project-123" in files[".env"]
    assert "BIGQUERY_LOCATION=us-central1" in files[".env"]

