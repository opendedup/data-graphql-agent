"""Docker build and startup validator."""

import asyncio
import time
from typing import Tuple
import httpx


class DockerValidator:
    """Validates Docker build and server startup."""

    async def validate_docker_build(self, temp_dir: str) -> Tuple[bool, str]:
        """Validate Docker build and server startup.

        Args:
            temp_dir: Directory containing generated files with Dockerfile

        Returns:
            Tuple of (is_valid, error_message)
        """
        container_id = None

        try:
            # Check if Docker is available
            check_docker = await asyncio.create_subprocess_exec(
                "docker",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check_docker.communicate()

            if check_docker.returncode != 0:
                return False, "Docker not found. Install Docker to enable full validation."

            # Build Docker image
            image_tag = f"test-graphql-api-{int(time.time())}"

            build_process = await asyncio.create_subprocess_exec(
                "docker",
                "build",
                "-t",
                image_tag,
                ".",
                cwd=temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                build_process.communicate(), timeout=120.0
            )

            if build_process.returncode != 0:
                error_output = stderr.decode() if stderr else stdout.decode()
                return False, f"Docker build failed:\n{error_output[:500]}"

            # Start container
            run_process = await asyncio.create_subprocess_exec(
                "docker",
                "run",
                "-d",
                "--name",
                f"test-{image_tag}",
                "-p",
                "14000:4000",  # Use alternative port to avoid conflicts
                "-e",
                "BIGQUERY_PROJECT_ID=test-project",
                "-e",
                "NODE_ENV=development",
                image_tag,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                run_process.communicate(), timeout=10.0
            )

            if run_process.returncode != 0:
                error_output = stderr.decode() if stderr else stdout.decode()
                await self._cleanup_docker(image_tag, None)
                return False, f"Failed to start container:\n{error_output}"

            container_id = stdout.decode().strip()

            # Wait for server to start
            await asyncio.sleep(5)

            # Check if container is still running
            check_process = await asyncio.create_subprocess_exec(
                "docker",
                "ps",
                "-q",
                "-f",
                f"id={container_id}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, _ = await check_process.communicate()

            if not stdout.decode().strip():
                # Container stopped, get logs
                logs_process = await asyncio.create_subprocess_exec(
                    "docker",
                    "logs",
                    container_id,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                logs_stdout, logs_stderr = await logs_process.communicate()
                logs = logs_stderr.decode() if logs_stderr else logs_stdout.decode()

                await self._cleanup_docker(image_tag, container_id)
                return False, f"Container stopped unexpectedly:\n{logs[:500]}"

            # Try to connect to health endpoint
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "http://localhost:14000/.well-known/apollo/server-health",
                        timeout=5.0,
                    )

                    if response.status_code != 200:
                        await self._cleanup_docker(image_tag, container_id)
                        return False, f"Health check failed with status {response.status_code}"

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                await self._cleanup_docker(image_tag, container_id)
                return False, f"Could not connect to server: {str(e)}"

            # Success! Cleanup
            await self._cleanup_docker(image_tag, container_id)
            return True, ""

        except asyncio.TimeoutError:
            await self._cleanup_docker(None, container_id)
            return False, "Docker validation timeout"
        except Exception as e:
            await self._cleanup_docker(None, container_id)
            return False, f"Docker validation error: {str(e)}"

    async def _cleanup_docker(
        self, image_tag: str | None, container_id: str | None
    ) -> None:
        """Clean up Docker resources.

        Args:
            image_tag: Docker image tag to remove
            container_id: Container ID to stop and remove
        """
        try:
            # Stop and remove container
            if container_id:
                await asyncio.create_subprocess_exec(
                    "docker",
                    "stop",
                    container_id,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.create_subprocess_exec(
                    "docker",
                    "rm",
                    container_id,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )

            # Remove image
            if image_tag:
                await asyncio.create_subprocess_exec(
                    "docker",
                    "rmi",
                    image_tag,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
        except Exception:
            # Ignore cleanup errors
            pass

