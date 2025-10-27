"""MCP tool handlers for executing tool requests."""

import os
import logging
from datetime import datetime
from typing import Any, Dict
import traceback

from ..models.request_models import GenerateGraphQLRequest, ValidateSchemaRequest
from ..models.response_models import (
    GenerateGraphQLResponse,
    ValidateSchemaResponse,
    FileManifest,
)
from ..generation.project_generator import ProjectGenerator
from ..clients.storage_client import StorageClient
from ..validation import CodeValidator, ValidationLevel
from .config import load_config

logger = logging.getLogger(__name__)


async def handle_generate_graphql_api(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle generate_graphql_api tool request with validation.

    Args:
        arguments: Tool arguments from MCP client

    Returns:
        Response dictionary with generation results
    """
    try:
        # Load configuration
        config = load_config()

        # Validate and parse request
        logger.info("Parsing and validating request...")
        request = GenerateGraphQLRequest(**arguments)
        logger.info("Request validated successfully.")

        # Parse validation settings
        validation_level_str = arguments.get("validation_level", "standard")
        validation_level = ValidationLevel(validation_level_str)
        auto_fix = arguments.get("auto_fix", False)

        # Determine base output path
        base_output_path = request.output_path or config.graphql_output_dir
        
        # Create timestamped subfolder: project_name/graphql_<timestamp>/
        # Convert to lowercase for case-insensitive folder names
        sanitized_project_name = request.project_name.lower().replace(' ', '_').replace('-', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(base_output_path, sanitized_project_name, f'graphql_{timestamp}')

        # Generate project
        logger.info("Initializing ProjectGenerator...")
        project_generator = ProjectGenerator(config.gcp_project_id)
        logger.info("Generating project files...")
        
        # Prepare API metadata for schema generation
        api_metadata = None
        if request.insight or request.summary or request.dataset_count or request.execution_time_ms:
            api_metadata = {
                "insight": request.insight,
                "summary": request.summary,
                "dataset_count": request.dataset_count,
                "execution_time_ms": request.execution_time_ms,
                "total_queries": len(request.queries),
            }
        
        generated_files = project_generator.generate_project(
            project_name=request.project_name,
            queries=request.queries,
            api_metadata=api_metadata,
        )
        logger.info(f"{len(generated_files)} project files generated in memory.")

        # Validate generated code
        logger.info("Initializing CodeValidator...")
        validator = CodeValidator(config.gcp_project_id)
        logger.info(f"Starting code validation (level: {validation_level.value})...")
        validation_result = await validator.validate(
            files=generated_files,
            queries=request.queries,
            validation_level=validation_level,
        )
        logger.info("Code validation complete.")

        # Handle validation failures
        if not validation_result.is_valid:
            logger.error(f"Code validation failed at {validation_level.value} level")
            logger.error(f"Validation errors: {validation_result.errors}")
            
            if validation_result.can_auto_fix:
                logger.info("Auto-fix is available but not enabled. To enable it, set 'auto_fix': true in your request arguments.")
            
            if auto_fix and validation_result.can_auto_fix:
                # TODO: Implement auto-fix logic
                # For now, just return the error
                pass

            # Return validation errors without writing files
            error_response = GenerateGraphQLResponse(
                success=False,
                output_path=output_path,
                files_generated=[],
                message=f"Code validation failed at {validation_level.value} level",
                error=f"Validation errors: {'; '.join(validation_result.errors[:3])}",
            )
            return error_response.model_dump()

        # Write validated files to storage
        logger.info("Writing validated files to storage...")
        storage_client = StorageClient(config.gcp_project_id)
        file_manifests = storage_client.write_files(output_path, generated_files)
        logger.info("Files written successfully.")

        # Build response with validation results
        response = GenerateGraphQLResponse(
            success=True,
            output_path=output_path,
            files_generated=[FileManifest(**manifest) for manifest in file_manifests],
            message=f"Successfully generated and validated Apollo GraphQL Server with {len(request.queries)} queries. "
            f"Generated {len(file_manifests)} files at {output_path}. "
            f"Validation: {len(validation_result.checks_passed)} checks passed in {validation_result.duration_seconds:.1f}s",
        )

        return response.model_dump()

    except Exception as e:
        logger.error(f"Failed to generate GraphQL API: {e}", exc_info=True)
        error_response = GenerateGraphQLResponse(
            success=False,
            output_path=arguments.get("output_path", ""),
            files_generated=[],
            message=f"Failed to generate GraphQL API: {str(e)}",
            error=str(e),
        )
        return error_response.model_dump()


async def handle_validate_graphql_schema(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle validate_graphql_schema tool request.

    Args:
        arguments: Tool arguments from MCP client

    Returns:
        Response dictionary with validation results
    """
    try:
        # Validate and parse request
        request = ValidateSchemaRequest(**arguments)

        # Read schema file
        with open(request.schema_path, "r") as f:
            schema_content = f.read()

        # Basic validation (check for syntax issues)
        errors = []
        warnings = []

        # Check for basic GraphQL syntax
        if "type Query" not in schema_content:
            errors.append("Schema must contain a Query type")

        if "{" not in schema_content or "}" not in schema_content:
            errors.append("Schema has invalid syntax (missing braces)")

        # Check for common issues
        if "type query" in schema_content.lower() and "type Query" not in schema_content:
            warnings.append("Query type should be capitalized as 'type Query'")

        # Build response
        response = ValidateSchemaResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            message="Schema is valid"
            if len(errors) == 0
            else f"Schema has {len(errors)} errors",
        )

        return response.model_dump()

    except FileNotFoundError:
        error_response = ValidateSchemaResponse(
            valid=False,
            errors=[f"Schema file not found: {arguments.get('schema_path')}"],
            warnings=[],
            message="Schema file not found",
        )
        return error_response.model_dump()

    except Exception as e:
        error_response = ValidateSchemaResponse(
            valid=False,
            errors=[str(e)],
            warnings=[],
            message=f"Validation failed: {str(e)}",
        )
        return error_response.model_dump()


# Tool handler registry
TOOL_HANDLERS = {
    "generate_graphql_api": handle_generate_graphql_api,
    "validate_graphql_schema": handle_validate_graphql_schema,
}


async def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Route tool call to appropriate handler.

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments

    Returns:
        Tool execution results

    Raises:
        ValueError: If tool name is not recognized
    """
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        raise ValueError(f"Unknown tool: {tool_name}")

    return await handler(arguments)

