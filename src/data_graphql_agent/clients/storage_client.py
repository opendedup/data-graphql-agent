"""Storage client for writing generated code to GCS or local filesystem."""

import os
from pathlib import Path
from typing import Dict, List, Tuple
from google.cloud import storage


class StorageClient:
    """Client for writing files to GCS or local filesystem."""

    def __init__(self, project_id: str):
        """Initialize storage client.

        Args:
            project_id: Google Cloud Project ID
        """
        self.project_id = project_id
        self._gcs_client = None

    @property
    def gcs_client(self) -> storage.Client:
        """Get or create GCS client lazily.

        Returns:
            storage.Client: Google Cloud Storage client
        """
        if self._gcs_client is None:
            self._gcs_client = storage.Client(project=self.project_id)
        return self._gcs_client

    def parse_path(self, path: str) -> Tuple[str, str, str]:
        """Parse output path into type, bucket/directory, and prefix.

        Args:
            path: Output path (gs://bucket/path, file:///path, or /path)

        Returns:
            Tuple of (storage_type, location, prefix)
            - storage_type: 'gcs' or 'local'
            - location: bucket name or directory path
            - prefix: path prefix within bucket/directory

        Raises:
            ValueError: If path format is invalid
        """
        if path.startswith("gs://"):
            # GCS path: gs://bucket/path/to/output
            parts = path[5:].split("/", 1)
            bucket_name = parts[0]
            prefix = parts[1] if len(parts) > 1 else ""
            return ("gcs", bucket_name, prefix)
        elif path.startswith("file://"):
            # File URL: file:///absolute/path
            local_path = path[7:]
            return ("local", local_path, "")
        else:
            # Absolute or relative path
            return ("local", path, "")

    def write_files(
        self, output_path: str, files: Dict[str, str]
    ) -> List[Dict[str, any]]:
        """Write multiple files to storage.

        Args:
            output_path: Base output path (gs://, file://, or local path)
            files: Dictionary mapping relative file paths to file contents

        Returns:
            List of file manifests with path, size, and description

        Raises:
            ValueError: If output path format is invalid
            Exception: If file writing fails
        """
        storage_type, location, prefix = self.parse_path(output_path)

        if storage_type == "gcs":
            return self._write_to_gcs(location, prefix, files)
        else:
            return self._write_to_local(location, files)

    def _write_to_gcs(
        self, bucket_name: str, prefix: str, files: Dict[str, str]
    ) -> List[Dict[str, any]]:
        """Write files to Google Cloud Storage.

        Args:
            bucket_name: GCS bucket name
            prefix: Path prefix within bucket
            files: Dictionary mapping relative paths to contents

        Returns:
            List of file manifests
        """
        bucket = self.gcs_client.bucket(bucket_name)
        manifests = []

        for relative_path, content in files.items():
            # Construct full GCS path
            blob_path = f"{prefix}/{relative_path}" if prefix else relative_path
            blob = bucket.blob(blob_path)

            # Upload content
            if isinstance(content, str):
                blob.upload_from_string(content, content_type="text/plain")
                size = len(content.encode("utf-8"))
            else:
                blob.upload_from_string(content)
                size = len(content)

            manifests.append(
                {
                    "path": f"gs://{bucket_name}/{blob_path}",
                    "size_bytes": size,
                    "description": self._get_file_description(relative_path),
                }
            )

        return manifests

    def _write_to_local(
        self, base_path: str, files: Dict[str, str]
    ) -> List[Dict[str, any]]:
        """Write files to local filesystem.

        Args:
            base_path: Base directory path
            files: Dictionary mapping relative paths to contents

        Returns:
            List of file manifests
        """
        base_dir = Path(base_path)
        base_dir.mkdir(parents=True, exist_ok=True)
        manifests = []

        for relative_path, content in files.items():
            file_path = base_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            if isinstance(content, str):
                file_path.write_text(content, encoding="utf-8")
            else:
                file_path.write_bytes(content)

            size = file_path.stat().st_size

            manifests.append(
                {
                    "path": str(file_path),
                    "size_bytes": size,
                    "description": self._get_file_description(relative_path),
                }
            )

        return manifests

    def _get_file_description(self, file_path: str) -> str:
        """Get human-readable description of file based on path.

        Args:
            file_path: Relative file path

        Returns:
            Description string
        """
        descriptions = {
            "package.json": "Node.js package configuration",
            "tsconfig.json": "TypeScript compiler configuration",
            "Dockerfile": "Docker container configuration",
            "docker-compose.yml": "Docker Compose orchestration",
            "docker-compose.test.yml": "Docker Compose test configuration",
            ".dockerignore": "Docker ignore patterns",
            ".gitignore": "Git ignore patterns",
            "README.md": "Project documentation",
            "src/server.ts": "Main Apollo Server entry point",
            "src/typeDefs.ts": "GraphQL schema definitions",
            "src/resolvers.ts": "GraphQL resolver implementations",
            "src/scalars.ts": "Custom GraphQL scalar type implementations",
            "src/types.ts": "TypeScript type definitions",
        }

        # Check for exact matches
        if file_path in descriptions:
            return descriptions[file_path]

        # Check for pattern matches
        if file_path.startswith("src/resolvers/"):
            return "GraphQL resolver function"
        elif file_path.startswith("test-client/"):
            return "Test client file"
        elif file_path.startswith("tests/"):
            return "Integration test"
        elif file_path.endswith(".ts"):
            return "TypeScript source file"
        elif file_path.endswith(".json"):
            return "JSON configuration file"
        else:
            return "Generated file"

