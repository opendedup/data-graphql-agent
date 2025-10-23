"""Test schema generator."""

from typing import TYPE_CHECKING
from unittest.mock import Mock, MagicMock

import pytest
from google.cloud import bigquery

from data_graphql_agent.generation.schema_generator import SchemaGenerator

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def schema_generator(mocker: "MockerFixture") -> SchemaGenerator:
    """Create schema generator fixture.

    Args:
        mocker: Pytest mocker fixture

    Returns:
        SchemaGenerator instance with mocked client
    """
    mocker.patch("google.cloud.bigquery.Client")
    return SchemaGenerator(project_id="test-project")


def test_type_mapping(schema_generator: SchemaGenerator) -> None:
    """Test BigQuery to GraphQL type mapping."""
    assert schema_generator.TYPE_MAPPING["STRING"] == "String"
    assert schema_generator.TYPE_MAPPING["INT64"] == "Int"
    assert schema_generator.TYPE_MAPPING["FLOAT64"] == "Float"
    assert schema_generator.TYPE_MAPPING["BOOL"] == "Boolean"


def test_to_pascal_case(schema_generator: SchemaGenerator) -> None:
    """Test conversion to PascalCase."""
    assert schema_generator._to_pascal_case("test_name") == "TestName"
    assert schema_generator._to_pascal_case("camelCase") == "Camelcase"
    assert schema_generator._to_pascal_case("simple") == "Simple"


def test_generate_nested_type_name(schema_generator: SchemaGenerator) -> None:
    """Test nested type name generation."""
    name1 = schema_generator._generate_nested_type_name("ParentType", "child_field")
    assert name1 == "ParentType_ChildField"

    # Test collision handling
    name2 = schema_generator._generate_nested_type_name("ParentType", "child_field")
    assert name2 == "ParentType_ChildField1"


def test_field_to_graphql_type_primitive(
    schema_generator: SchemaGenerator,
) -> None:
    """Test converting primitive field to GraphQL type."""
    field = bigquery.SchemaField("test_field", "STRING", mode="NULLABLE")

    graphql_type, nested_types = schema_generator._field_to_graphql_type(
        field, "TestType"
    )

    assert graphql_type == "String"
    assert len(nested_types) == 0


def test_field_to_graphql_type_array(
    schema_generator: SchemaGenerator,
) -> None:
    """Test converting array field to GraphQL type."""
    field = bigquery.SchemaField("test_array", "STRING", mode="REPEATED")

    graphql_type, nested_types = schema_generator._field_to_graphql_type(
        field, "TestType"
    )

    assert graphql_type == "[String]"
    assert len(nested_types) == 0


def test_field_to_graphql_type_struct(
    schema_generator: SchemaGenerator,
) -> None:
    """Test converting STRUCT field to GraphQL type."""
    nested_fields = [
        bigquery.SchemaField("city", "STRING"),
        bigquery.SchemaField("country", "STRING"),
    ]
    field = bigquery.SchemaField(
        "location", "STRUCT", mode="NULLABLE", fields=nested_fields
    )

    graphql_type, nested_types = schema_generator._field_to_graphql_type(
        field, "TestType"
    )

    assert graphql_type == "TestType_Location"
    assert len(nested_types) > 0
    assert "type TestType_Location" in nested_types[0]


def test_generate_types_from_schema(
    schema_generator: SchemaGenerator,
) -> None:
    """Test generating types from BigQuery schema."""
    schema = [
        bigquery.SchemaField("id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("name", "STRING", mode="NULLABLE"),
    ]

    types, field_metadata = schema_generator._generate_types_from_schema(
        "TestResult", schema
    )

    assert len(types) == 1
    assert "type TestResult" in types[0]
    assert "id: Int" in types[0]
    assert "name: String" in types[0]

    assert len(field_metadata) == 2
    assert field_metadata[0]["name"] == "id"
    assert field_metadata[1]["name"] == "name"

