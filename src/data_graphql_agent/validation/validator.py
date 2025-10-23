"""Main code validator coordinating all validation levels."""

import tempfile
import shutil
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path

from pydantic import BaseModel

from ..models.request_models import QueryInput
from .graphql_validator import GraphQLValidator
from .sql_validator import SQLValidator
from .typescript_validator import TypeScriptValidator
from .docker_validator import DockerValidator


class ValidationLevel(str, Enum):
    """Validation thoroughness levels."""

    QUICK = "quick"  # ~1 second
    STANDARD = "standard"  # ~10 seconds
    FULL = "full"  # ~60 seconds


class ValidationResult(BaseModel):
    """Result of code validation."""

    is_valid: bool
    level: ValidationLevel
    checks_passed: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    fix_suggestions: List[str] = []
    can_auto_fix: bool = False
    duration_seconds: float = 0.0


class CodeValidator:
    """Validates generated Apollo Server code before writing."""

    def __init__(self, project_id: str):
        """Initialize code validator.

        Args:
            project_id: Google Cloud Project ID
        """
        self.project_id = project_id
        self.graphql_validator = GraphQLValidator()
        self.sql_validator = SQLValidator(project_id)
        self.typescript_validator = TypeScriptValidator()
        self.docker_validator = DockerValidator()

    async def validate(
        self,
        files: Dict[str, str],
        queries: List[QueryInput],
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> ValidationResult:
        """Validate generated code at specified level.

        Args:
            files: Dictionary mapping file paths to file contents
            queries: List of query inputs
            validation_level: Level of validation to perform

        Returns:
            ValidationResult with validation status and details
        """
        import time

        start_time = time.time()

        result = ValidationResult(
            is_valid=True,
            level=validation_level,
        )

        try:
            # Level 1: Quick validation (always run)
            await self._run_quick_validation(files, queries, result)

            if not result.is_valid and validation_level == ValidationLevel.QUICK:
                result.duration_seconds = time.time() - start_time
                return result

            # Level 2: Standard validation
            if validation_level in [ValidationLevel.STANDARD, ValidationLevel.FULL]:
                await self._run_standard_validation(files, result)

            if not result.is_valid and validation_level == ValidationLevel.STANDARD:
                result.duration_seconds = time.time() - start_time
                return result

            # Level 3: Full validation
            if validation_level == ValidationLevel.FULL:
                await self._run_full_validation(files, result)

        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation failed: {str(e)}")

        result.duration_seconds = time.time() - start_time
        return result

    async def _run_quick_validation(
        self,
        files: Dict[str, str],
        queries: List[QueryInput],
        result: ValidationResult,
    ) -> None:
        """Run quick validation checks (~1 second).

        Args:
            files: Generated files
            queries: Query inputs
            result: Validation result to update
        """
        # 1. Validate GraphQL schema syntax
        schema_content = files.get("src/typeDefs.ts", "")
        if schema_content:
            schema_errors = self.graphql_validator.validate_schema(schema_content)
            if schema_errors:
                result.is_valid = False
                result.errors.extend(schema_errors)
            else:
                result.checks_passed.append("GraphQL schema syntax")

        # 2. Validate BigQuery SQL queries
        sql_errors = await self.sql_validator.validate_queries(queries)
        if sql_errors:
            result.is_valid = False
            result.errors.extend(sql_errors)
        else:
            result.checks_passed.append("BigQuery SQL dry-run")

        # 3. Check file structure
        required_files = [
            "package.json",
            "tsconfig.json",
            "src/server.ts",
            "src/typeDefs.ts",
            "src/resolvers.ts",
            "src/lineage.ts",
            "src/context.ts",
            "src/errors.ts",
        ]

        missing_files = [f for f in required_files if f not in files]
        if missing_files:
            result.is_valid = False
            result.errors.append(
                f"Missing required files: {', '.join(missing_files)}"
            )
        else:
            result.checks_passed.append("File structure completeness")

        # 4. Basic JSON validation for package.json
        import json

        try:
            json.loads(files.get("package.json", "{}"))
            result.checks_passed.append("package.json syntax")
        except json.JSONDecodeError as e:
            result.is_valid = False
            result.errors.append(f"Invalid package.json: {str(e)}")

    async def _run_standard_validation(
        self, files: Dict[str, str], result: ValidationResult
    ) -> None:
        """Run standard validation checks (~10 seconds).

        Args:
            files: Generated files
            result: Validation result to update
        """
        # Write files to temporary directory for TypeScript compilation check
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write all files
            for file_path, content in files.items():
                full_path = temp_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")

            # Run TypeScript compilation check
            is_valid, error_message = await self.typescript_validator.validate_compilation(
                temp_dir
            )

            if not is_valid:
                result.is_valid = False
                result.errors.append(f"TypeScript compilation failed: {error_message}")
            else:
                result.checks_passed.append("TypeScript compilation")

            # Check import paths
            import_errors = self._check_import_paths(files)
            if import_errors:
                result.warnings.extend(import_errors)
            else:
                result.checks_passed.append("Import path validation")

    async def _run_full_validation(
        self, files: Dict[str, str], result: ValidationResult
    ) -> None:
        """Run full validation checks (~60 seconds).

        Args:
            files: Generated files
            result: Validation result to update
        """
        # Write files to temporary directory for Docker build
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write all files
            for file_path, content in files.items():
                full_path = temp_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")

            # Run Docker build and startup test
            is_valid, error_message = await self.docker_validator.validate_docker_build(
                temp_dir
            )

            if not is_valid:
                result.is_valid = False
                result.errors.append(f"Docker validation failed: {error_message}")
            else:
                result.checks_passed.extend([
                    "Docker build test",
                    "Server startup verification",
                    "Health check endpoint",
                ])

    def _check_import_paths(self, files: Dict[str, str]) -> List[str]:
        """Check that import paths are valid.

        Args:
            files: Generated files

        Returns:
            List of import path issues
        """
        warnings = []

        # Check for common import issues
        for file_path, content in files.items():
            if not file_path.endswith(".ts"):
                continue

            # Check for imports from non-existent files
            import re

            imports = re.findall(r"from ['\"](.+)['\"]", content)
            for import_path in imports:
                if import_path.startswith("."):
                    # Relative import
                    resolved_path = self._resolve_import_path(file_path, import_path)
                    if resolved_path and resolved_path not in files:
                        warnings.append(
                            f"Import '{import_path}' in {file_path} may be invalid"
                        )

        return warnings

    def _resolve_import_path(
        self, from_file: str, import_path: str
    ) -> Optional[str]:
        """Resolve relative import path.

        Args:
            from_file: File containing the import
            import_path: Relative import path

        Returns:
            Resolved file path or None
        """
        from pathlib import Path

        base_path = Path(from_file).parent
        resolved = (base_path / import_path).with_suffix(".ts")
        return str(resolved)

