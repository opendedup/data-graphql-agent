"""GraphQL schema generator from BigQuery SQL queries."""

import logging
from typing import Dict, List, Set, Tuple, Optional
from google.cloud import bigquery

logger = logging.getLogger(__name__)


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
        "TIMESTAMP": "DateTime",  # Custom scalar for ISO 8601 timestamps
        "DATE": "DateTime",  # Custom scalar for ISO 8601 dates
        "DATETIME": "DateTime",  # Custom scalar for ISO 8601 datetimes
        "TIME": "String",  # Keep TIME as String (HH:MM:SS format)
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
        self, queries: List[Dict[str, any]], api_metadata: Optional[Dict[str, any]] = None
    ) -> Tuple[str, Dict[str, List[Dict[str, any]]]]:
        """Generate complete GraphQL schema from multiple queries.

        Args:
            queries: List of query dictionaries with 'queryName' and 'sql'
            api_metadata: Optional metadata about the API (insight, summary, etc.)

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
            
            # Get field descriptions from query validation metadata if available
            field_descriptions = {}
            if "validation_details" in query and query["validation_details"]:
                result_schema = query["validation_details"].get("result_schema")
                if result_schema:
                    for field_info in result_schema:
                        if "description" in field_info and field_info["description"]:
                            field_descriptions[field_info["name"]] = field_info["description"]
                    
                    if field_descriptions:
                        logger.info(f"Found {len(field_descriptions)} field descriptions for {query_name}")

            # Generate GraphQL types for this query
            return_type_name = self._to_pascal_case(query_name) + "Result"
            types, field_defs = self._generate_types_from_schema(
                return_type_name, schema, field_descriptions
            )

            # Add custom types (if not already added)
            for type_def in types:
                if type_def not in custom_types:
                    custom_types.append(type_def)

            # Add query field with description if available
            query_field = self._format_query_field(query_name, return_type_name, query)
            query_types.append(query_field)

            # Store field schema for validation
            field_schemas[query_name] = field_defs

        # Build complete schema
        schema_parts = []

        # Add custom scalar definitions if needed
        if self._uses_datetime_scalar(custom_types, query_types):
            schema_parts.append('"""')
            schema_parts.append("Custom scalar for date and time values.")
            schema_parts.append("Accepts and returns ISO 8601 formatted strings (e.g., '2025-10-26T20:30:00Z').")
            schema_parts.append('"""')
            schema_parts.append("scalar DateTime")
            schema_parts.append("")

        # Add custom types
        if custom_types:
            schema_parts.extend(custom_types)
            schema_parts.append("")

        # Add Query type with description if metadata available
        query_type_description = self._format_query_type_description(api_metadata)
        if query_type_description:
            schema_parts.append(query_type_description)
        
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

    def _sanitize_description(self, description: str) -> str:
        """
        Sanitize description for safe use in GraphQL schema.
        
        Removes or replaces problematic characters that can cause GraphQL parsing errors.
        Handles both field descriptions and query-level descriptions.
        
        Args:
            description: Raw description text
            
        Returns:
            Sanitized description safe for GraphQL
        """
        if not description:
            return ""
        
        # Remove common prefixes from query generation
        desc = description.replace("Brief description: ", "")
        
        # Replace square brackets (cause GraphQL parsing errors)
        desc = desc.replace("[", "(").replace("]", ")")
        
        # Escape backslashes first (must be done before other escapes)
        desc = desc.replace('\\', '\\\\')
        
        # Escape quotes for GraphQL string literals
        desc = desc.replace('"', '\\"')
        
        # For template literal embedding (in TypeScript comments)
        desc = desc.replace('`', '\\`').replace('$', '\\$')
        
        return desc.strip()

    def _generate_types_from_schema(
        self, type_name: str, schema: List[bigquery.SchemaField],
        field_descriptions: Optional[Dict[str, str]] = None
    ) -> Tuple[List[str], List[Dict[str, any]]]:
        """Generate GraphQL types from BigQuery schema.

        Args:
            type_name: Name for the root type
            schema: BigQuery schema fields
            field_descriptions: Optional dict mapping field names to descriptions

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
            
            # Add description if available
            field_desc = field_descriptions.get(field.name) if field_descriptions else None
            if field_desc:
                # Sanitize description for GraphQL
                sanitized_desc = self._sanitize_description(field_desc)
                field_lines.append(f'  """')
                field_lines.append(f'  {sanitized_desc}')
                field_lines.append(f'  """')

            # Add field to type definition
            field_lines.append(f"  {field.name}: {graphql_type}")

            # Store field metadata
            field_metadata.append(
                {
                    "name": field.name,
                    "type": graphql_type,
                    "bigquery_type": field.field_type,
                    "nullable": field.mode != "REQUIRED",
                    "description": field_desc
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

    def _uses_datetime_scalar(self, custom_types: List[str], query_types: List[str]) -> bool:
        """Check if any types use the DateTime scalar.

        Args:
            custom_types: List of custom type definitions
            query_types: List of query type definitions

        Returns:
            True if DateTime scalar is used
        """
        all_types = "\n".join(custom_types + query_types)
        return "DateTime" in all_types

    def _format_query_field(
        self, query_name: str, return_type_name: str, query: Dict[str, any]
    ) -> str:
        """Format a query field with optional description and metadata.

        Args:
            query_name: GraphQL query field name
            return_type_name: GraphQL return type name
            query: Query dictionary with optional description, alignment_score, etc.

        Returns:
            Formatted query field string with description
        """
        description = query.get("description", "")
        alignment_score = query.get("alignment_score")
        iterations = query.get("iterations")
        generation_time_ms = query.get("generation_time_ms")

        if not description and not alignment_score:
            # No metadata, return simple field
            return f"  {query_name}: [{return_type_name}]"

        # Build description with metadata
        lines = []
        if description:
            # Sanitize description for GraphQL
            sanitized_desc = self._sanitize_description(description)
            lines.append(f"  {sanitized_desc}")
        
        # Add performance metadata if available
        metadata_parts = []
        if alignment_score is not None:
            metadata_parts.append(f"Alignment {alignment_score:.2f}")
        if iterations is not None:
            metadata_parts.append(f"{iterations} iteration{'s' if iterations != 1 else ''}")
        if generation_time_ms is not None:
            gen_time_s = generation_time_ms / 1000
            metadata_parts.append(f"{gen_time_s:.1f}s generation")
        
        if metadata_parts:
            lines.append(f"  ")
            lines.append(f"  Performance: {' | '.join(metadata_parts)}")

        # Format as GraphQL description
        description_text = "\n".join(lines)
        return f'  """\n{description_text}\n  """\n  {query_name}: [{return_type_name}]'

    def _format_query_type_description(self, api_metadata: Optional[Dict[str, any]]) -> str:
        """Format Query type description from API metadata.

        Args:
            api_metadata: Optional dict with insight, summary, dataset_count, etc.

        Returns:
            Formatted GraphQL description string or empty string
        """
        if not api_metadata:
            return ""

        lines = []
        
        # Add insight/purpose if available
        insight = api_metadata.get("insight", "")
        if insight:
            # Extract the main purpose from insight
            if ":" in insight:
                purpose = insight.split(":", 1)[1].strip()
            else:
                purpose = insight
            # Sanitize description for GraphQL
            sanitized_purpose = self._sanitize_description(purpose)
            lines.append(sanitized_purpose)
            lines.append("")

        # Add generation stats
        stats = []
        dataset_count = api_metadata.get("dataset_count")
        total_queries = api_metadata.get("total_queries")
        execution_time_ms = api_metadata.get("execution_time_ms")

        if dataset_count:
            stats.append(f"Datasets Analyzed: {dataset_count}")
        if total_queries:
            stats.append(f"Queries Generated: {total_queries} validated variants")
        if execution_time_ms:
            exec_time_s = execution_time_ms / 1000
            stats.append(f"Total Generation Time: {exec_time_s:.0f}s")

        if stats:
            lines.append("Generation Stats:")
            for stat in stats:
                lines.append(f"- {stat}")

        if not lines:
            return ""

        description_text = "\n".join(lines)
        return f'"""\n{description_text}\n"""'

