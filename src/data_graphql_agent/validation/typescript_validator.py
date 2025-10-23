"""TypeScript compilation validator."""

import subprocess
import asyncio
from typing import Tuple
from pathlib import Path


class TypeScriptValidator:
    """Validates TypeScript code compilation."""

    async def validate_compilation(self, temp_dir: str) -> Tuple[bool, str]:
        """Validate TypeScript compilation without emitting files.

        Args:
            temp_dir: Directory containing generated TypeScript files

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if npx is available
            check_npx = await asyncio.create_subprocess_exec(
                "which",
                "npx",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check_npx.communicate()

            if check_npx.returncode != 0:
                return False, "npx not found. Install Node.js to enable TypeScript validation."

            # Run tsc --noEmit to check compilation without generating files
            process = await asyncio.create_subprocess_exec(
                "npx",
                "tsc",
                "--noEmit",
                "--skipLibCheck",
                cwd=temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)

            if process.returncode != 0:
                error_output = stderr.decode() if stderr else stdout.decode()
                return False, f"TypeScript compilation errors:\n{error_output}"

            return True, ""

        except asyncio.TimeoutError:
            return False, "TypeScript compilation timeout (>30 seconds)"
        except FileNotFoundError as e:
            return False, f"Command not found: {str(e)}"
        except Exception as e:
            return False, f"TypeScript validation error: {str(e)}"

    async def check_typescript_installed(self) -> bool:
        """Check if TypeScript/npx is available.

        Returns:
            True if TypeScript can be used for validation
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "npx",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except (FileNotFoundError, Exception):
            return False

