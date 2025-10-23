"""GraphQL schema generator from BigQuery SQL queries."""

from typing import Dict, List, Set, Tuple, Optional
from google.cloud import bigquery


class SchemaGenerator:
    """Generates GraphQL schema from BigQuery query results."""

    # Mapping from BigQuery types to GraphQL scalar types
    TYPE_MAPPING = {
        "STRING": "String",
        "INT64": "Int",
        "INTEGER": "Int",
        "FLOAT64": "Float",
        "FLOAT": "Float",
        "BOOL": "Boolean",
        "BOOLEAN": "Boolean",
        "TIMESTAMP": "String",  # ISO 8601 format
        "DATE": "String",  # ISO 8601 format
        "DATETIME": "String",  # ISO 8601 format
        "TIME": "String",
        "NUMERIC": "Float",
        "BIGNUMERIC": "Float",
        "BYTES": "String",  # Base64 encoded
        "GEOGRAPHY": "String",  # WKT format
        "JSON": "String",  # JSON string
    }

    def __init__(self, project_id: str):
        """Initialize schema generator.

        Args:
            project_id: Google Cloud Project ID
        """
        self.project_id = project_id
        self.client = bigquery.Client(project=project_id)
        self.type_registry: Dict[str, str] = {}  # Track generated types

    def generate_schema_from_queries(
        self, queries: List[Dict[str, any]]
    ) -> Tuple[str, Dict[str, List[Dict[str, any]]]]:
        """Generate complete GraphQL schema from multiple queries.

        Args:
            queries: List of query dictionaries with 'queryName' and 'sql'

        Returns:
            Tuple of (schema string, query field schemas dict)
        """
        query_types: List[str] = []
        custom_types: List[str] = []
        field_schemas: Dict[str, List[Dict[str, any]]] = {}

        for query in queries:
            query_name = query["queryName"]
            sql = query["sql"]

            # Get schema from BigQuery dry run
            schema = self._get_query_schema(sql)

            # Generate GraphQL types for this query
            return_type_name = self._to_pascal_case(query_name) + "Result"
            types, field_defs = self._generate_types_from_schema(
                return_type_name, schema
            )

            # Add custom types (if not already added)
            for type_def in types:
                if type_def not in custom_types:
                    custom_types.append(type_def)

            # Add query field
            query_types.append(f"  {query_name}: [{return_type_name}]")

            # Store field schema for validation
            field_schemas[query_name] = field_defs

        # Build complete schema
        schema_parts = []

        # Add custom types
        if custom_types:
            schema_parts.extend(custom_types)
            schema_parts.append("")

        # Add Query type
        schema_parts.append("type Query {")
        schema_parts.extend(query_types)
        schema_parts.append("}")

        return "\n".join(schema_parts), field_schemas

    def _get_query_schema(self, sql: str) -> List[bigquery.SchemaField]:
        """Get query result schema using BigQuery dry run.

        Args:
            sql: BigQuery SQL query

        Returns:
            List of schema fields

        Raises:
            Exception: If query is invalid
        """
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = self.client.query(sql, job_config=job_config)
        return list(query_job.schema)

    def _generate_types_from_schema(
        self, type_name: str, schema: List[bigquery.SchemaField]
    ) -> Tuple[List[str], List[Dict[str, any]]]:
        """Generate GraphQL types from BigQuery schema.

        Args:
            type_name: Name for the root type
            schema: BigQuery schema fields

        Returns:
            Tuple of (list of type definitions, list of field metadata)
        """
        types: List[str] = []
        field_lines: List[str] = []
        field_metadata: List[Dict[str, any]] = []

        for field in schema:
            graphql_type, nested_types = self._field_to_graphql_type(
                field, type_name
            )
            types.extend(nested_types)

            # Add field to type definition
            field_lines.append(f"  {field.name}: {graphql_type}")

            # Store field metadata
            field_metadata.append(
                {
                    "name": field.name,
                    "type": graphql_type,
                    "bigquery_type": field.field_type,
                    "nullable": field.mode != "REQUIRED",
                }
            )

        # Create the main type definition
        main_type = f"type {type_name} {{\n" + "\n".join(field_lines) + "\n}"
        types.append(main_type)

        return types, field_metadata

    def _field_to_graphql_type(
        self, field: bigquery.SchemaField, parent_type_name: str
    ) -> Tuple[str, List[str]]:
        """Convert BigQuery field to GraphQL type.

        Args:
            field: BigQuery schema field
            parent_type_name: Name of parent type (for nested type naming)

        Returns:
            Tuple of (GraphQL type string, list of nested type definitions)
        """
        nested_types: List[str] = []

        # Handle REPEATED (arrays)
        if field.mode == "REPEATED":
            base_type, nested = self._get_base_type(field, parent_type_name)
            nested_types.extend(nested)
            return f"[{base_type}]", nested_types

        # Handle regular fields
        base_type, nested = self._get_base_type(field, parent_type_name)
        nested_types.extend(nested)
        return base_type, nested_types

    def _get_base_type(
        self, field: bigquery.SchemaField, parent_type_name: str
    ) -> Tuple[str, List[str]]:
        """Get base GraphQL type for a field.

        Args:
            field: BigQuery schema field
            parent_type_name: Name of parent type

        Returns:
            Tuple of (base type string, nested type definitions)
        """
        nested_types: List[str] = []

        # Handle STRUCT/RECORD (nested objects)
        if field.field_type in ("STRUCT", "RECORD"):
            nested_type_name = self._generate_nested_type_name(
                parent_type_name, field.name
            )

            # Generate nested type recursively
            nested_type_def, _ = self._generate_types_from_schema(
                nested_type_name, field.fields
            )
            nested_types.extend(nested_type_def)

            return nested_type_name, nested_types

        # Handle primitive types
        graphql_type = self.TYPE_MAPPING.get(field.field_type, "String")
        return graphql_type, nested_types

    def _generate_nested_type_name(self, parent_name: str, field_name: str) -> str:
        """Generate unique name for nested type.

        Args:
            parent_name: Parent type name
            field_name: Field name

        Returns:
            Unique type name
        """
        # Convert field name to PascalCase
        field_pascal = self._to_pascal_case(field_name)

        # Create unique name
        type_name = f"{parent_name}_{field_pascal}"

        # Handle collisions
        counter = 1
        original_name = type_name
        while type_name in self.type_registry:
            type_name = f"{original_name}{counter}"
            counter += 1

        self.type_registry[type_name] = parent_name
        return type_name

    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase.

        Args:
            name: Input name (snake_case or camelCase)

        Returns:
            PascalCase name
        """
        # Split on underscores and capitalize each part
        parts = name.replace("-", "_").split("_")
        return "".join(part.capitalize() for part in parts if part)

