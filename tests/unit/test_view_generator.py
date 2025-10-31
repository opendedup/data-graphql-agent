"""Test view generator."""

from typing import TYPE_CHECKING

import pytest

from data_graphql_agent.generation.view_generator import ViewGenerator

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def view_generator(mocker: "MockerFixture") -> ViewGenerator:
    """Create view generator fixture.

    Args:
        mocker: Pytest mocker fixture

    Returns:
        ViewGenerator instance with mocked BigQuery client
    """
    mock_client = mocker.patch("google.cloud.bigquery.Client")
    return ViewGenerator(
        project_id="test-project-123",
        location="us-central1"
    )


def test_init_with_default_location(mocker: "MockerFixture") -> None:
    """Test ViewGenerator initialization with default location.

    Args:
        mocker: Pytest mocker fixture
    """
    mocker.patch("google.cloud.bigquery.Client")
    generator = ViewGenerator(project_id="test-project")
    
    assert generator.project_id == "test-project"
    assert generator.location == "US"


def test_init_with_custom_location(mocker: "MockerFixture") -> None:
    """Test ViewGenerator initialization with custom location.

    Args:
        mocker: Pytest mocker fixture
    """
    mocker.patch("google.cloud.bigquery.Client")
    generator = ViewGenerator(
        project_id="test-project",
        location="europe-west1"
    )
    
    assert generator.project_id == "test-project"
    assert generator.location == "europe-west1"


def test_sanitize_dataset_name(view_generator: ViewGenerator) -> None:
    """Test dataset name sanitization.

    Args:
        view_generator: ViewGenerator fixture
    """
    # Test with spaces and hyphens
    result = view_generator._sanitize_dataset_name("My Test Project")
    assert result == "my_test_project_graphql"
    
    # Test with special characters
    result = view_generator._sanitize_dataset_name("Project-Name-123")
    assert result == "project_name_123_graphql"
    
    # Test with mixed case
    result = view_generator._sanitize_dataset_name("CamelCaseProject")
    assert result == "camelcaseproject_graphql"


def test_sanitize_view_name(view_generator: ViewGenerator) -> None:
    """Test view name sanitization.

    Args:
        view_generator: ViewGenerator fixture
    """
    # Test camelCase to snake_case
    result = view_generator._sanitize_view_name("getUserData")
    assert result == "get_user_data"
    
    # Test PascalCase to snake_case
    result = view_generator._sanitize_view_name("GetUserData")
    assert result == "get_user_data"
    
    # Test already snake_case
    result = view_generator._sanitize_view_name("get_user_data")
    assert result == "get_user_data"
    
    # Test with numbers
    result = view_generator._sanitize_view_name("query123Data")
    assert result == "query123_data"


def test_create_views_for_queries(
    view_generator: ViewGenerator,
    mocker: "MockerFixture"
) -> None:
    """Test creating views for multiple queries.

    Args:
        view_generator: ViewGenerator fixture
        mocker: Pytest mocker fixture
    """
    # Mock the methods
    mocker.patch.object(
        view_generator,
        "_ensure_dataset_exists",
        return_value=None
    )
    mocker.patch.object(
        view_generator,
        "_create_view",
        side_effect=lambda dataset, name, sql: f"test-project-123.{dataset}.{view_generator._sanitize_view_name(name)}"
    )
    
    queries = [
        {
            "queryName": "getUserData",
            "sql": "SELECT * FROM users"
        },
        {
            "queryName": "getOrderInfo",
            "sql": "SELECT * FROM orders"
        }
    ]
    
    result = view_generator.create_views_for_queries("Test Project", queries)
    
    # Verify the view map
    assert "getUserData" in result
    assert "getOrderInfo" in result
    assert result["getUserData"] == "test-project-123.test_project_graphql.get_user_data"
    assert result["getOrderInfo"] == "test-project-123.test_project_graphql.get_order_info"
    
    # Verify dataset creation was called
    view_generator._ensure_dataset_exists.assert_called_once_with("test_project_graphql")
    
    # Verify views were created
    assert view_generator._create_view.call_count == 2

