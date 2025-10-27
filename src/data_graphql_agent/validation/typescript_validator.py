"""TypeScript compilation validator."""

import subprocess
import asyncio
import logging
from typing import Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


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

            # Install dependencies first
            logger.info("Installing npm dependencies...")
            install_process = await asyncio.create_subprocess_exec(
                "npm",
                "install",
                cwd=temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            install_stdout, install_stderr = await asyncio.wait_for(
                install_process.communicate(), 
                timeout=600.0  # 10 minutes for npm install
            )

            if install_process.returncode != 0:
                install_error = install_stderr.decode() if install_stderr else install_stdout.decode()
                logger.error(f"npm install failed: {install_error}")
                return False, f"npm install failed: {install_error}"

            logger.info("npm install completed successfully")

            # Run tsc --noEmit to check compilation without generating files
            logger.info("Running TypeScript compilation check...")
            process = await asyncio.create_subprocess_exec(
                "npx",
                "tsc",
                "--noEmit",
                "--skipLibCheck",
                cwd=temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300.0)

            # Log the full output regardless of success/failure
            if stdout:
                logger.debug(f"TypeScript compiler stdout:\n{stdout.decode()}")
            if stderr:
                logger.debug(f"TypeScript compiler stderr:\n{stderr.decode()}")

            if process.returncode != 0:
                error_output = stderr.decode() if stderr else stdout.decode()
                logger.error(f"TypeScript compilation failed. Error output:\n{error_output}")
                return False, f"TypeScript compilation errors:\n{error_output}"

            logger.info("TypeScript compilation succeeded.")
            return True, ""

        except asyncio.TimeoutError:
            logger.error("TypeScript compilation timed out after 5 minutes")
            return False, "TypeScript compilation timeout (>5 minutes)"
        except FileNotFoundError as e:
            logger.error(f"Command not found: {str(e)}", exc_info=True)
            return False, f"Command not found: {str(e)}"
        except Exception as e:
            logger.error(f"TypeScript validation error: {str(e)}", exc_info=True)
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

