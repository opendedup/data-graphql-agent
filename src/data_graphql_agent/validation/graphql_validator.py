"""GraphQL schema validator."""

import re
from typing import List


class GraphQLValidator:
    """Validates GraphQL schema syntax."""

    def validate_schema(self, schema_content: str) -> List[str]:
        """Validate GraphQL schema syntax.

        Args:
            schema_content: GraphQL schema content from typeDefs file

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Extract GraphQL schema from TypeScript template literal
        schema = self._extract_schema_from_template(schema_content)

        if not schema:
            errors.append("Could not extract GraphQL schema from typeDefs file")
            return errors

        # Check for Query type
        if not re.search(r"type\s+Query\s*\{", schema):
            errors.append("Schema must contain a Query type")

        # Check for balanced braces (excluding braces in description strings)
        # Remove description strings before counting braces
        schema_without_descriptions = re.sub(r'""".*?"""', '', schema, flags=re.DOTALL)
        open_braces = schema_without_descriptions.count("{")
        close_braces = schema_without_descriptions.count("}")
        if open_braces != close_braces:
            errors.append(
                f"Unbalanced braces in schema (open: {open_braces}, close: {close_braces})"
            )

        # Check for basic GraphQL syntax issues
        # Look for invalid type definitions
        invalid_type_pattern = r"type\s+[a-z]"  # Type names should start with uppercase
        if re.search(invalid_type_pattern, schema):
            errors.append("Type names must start with an uppercase letter")

        # Check for field syntax issues (basic check)
        # Fields should follow pattern: fieldName: Type
        lines = schema.split("\n")
        in_type_def = False
        for i, line in enumerate(lines, 1):
            line = line.strip()

            if line.startswith("type "):
                in_type_def = True
            elif in_type_def and "}" in line:
                in_type_def = False
            elif in_type_def and line and not line.startswith("#"):
                # Check if it looks like a field definition
                if ":" in line:
                    # Basic field syntax check
                    field_match = re.match(r"^\w+\s*:\s*[\[\]!\w]+", line)
                    if not field_match and not line.startswith("}"):
                        errors.append(
                            f"Line {i}: Possible syntax error in field definition: {line[:50]}"
                        )

        # Check for common mistakes
        if "type query" in schema.lower() and "type Query" not in schema:
            errors.append("Query type should be capitalized as 'type Query'")

        if "type Mutation" in schema and "type Query" not in schema:
            errors.append("Schema has Mutation type but no Query type")

        return errors

    def _extract_schema_from_template(self, content: str) -> str:
        """Extract GraphQL schema from TypeScript template literal.

        Args:
            content: Content of typeDefs.ts file

        Returns:
            Extracted GraphQL schema
        """
        # Look for template literal pattern: export const typeDefs = `...`;
        # Need to handle escaped backticks in the content
        match = re.search(r"export\s+const\s+typeDefs\s*=\s*`(.*?)`\s*;", content, re.DOTALL)
        if match:
            schema = match.group(1)
            # Unescape any escaped backticks for validation
            schema = schema.replace('\\`', '`').replace('\\$', '$')
            return schema

        # Alternative pattern with multiline template
        match = re.search(r"`\s*(type\s+\w+.*?)`", content, re.DOTALL)
        if match:
            schema = match.group(1)
            schema = schema.replace('\\`', '`').replace('\\$', '$')
            return schema

        return ""

