"""Test storage client."""

from typing import TYPE_CHECKING
from pathlib import Path
import tempfile
import shutil

import pytest
from unittest.mock import Mock, patch

from data_graphql_agent.clients.storage_client import StorageClient

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def storage_client() -> StorageClient:
    """Create storage client fixture.

    Returns:
        StorageClient instance
    """
    return StorageClient(project_id="test-project")


def test_parse_path_gcs(storage_client: StorageClient) -> None:
    """Test parsing GCS path."""
    storage_type, location, prefix = storage_client.parse_path(
        "gs://my-bucket/path/to/output"
    )

    assert storage_type == "gcs"
    assert location == "my-bucket"
    assert prefix == "path/to/output"


def test_parse_path_file_url(storage_client: StorageClient) -> None:
    """Test parsing file:// URL."""
    storage_type, location, prefix = storage_client.parse_path(
        "file:///absolute/path/to/output"
    )

    assert storage_type == "local"
    assert location == "/absolute/path/to/output"
    assert prefix == ""


def test_parse_path_absolute(storage_client: StorageClient) -> None:
    """Test parsing absolute path."""
    storage_type, location, prefix = storage_client.parse_path("/path/to/output")

    assert storage_type == "local"
    assert location == "/path/to/output"
    assert prefix == ""


def test_write_to_local(storage_client: StorageClient) -> None:
    """Test writing files to local filesystem."""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            "package.json": '{"name": "test"}',
            "src/index.ts": "console.log('test');",
        }

        manifests = storage_client._write_to_local(tmpdir, files)

        # Check files were created
        assert Path(tmpdir, "package.json").exists()
        assert Path(tmpdir, "src", "index.ts").exists()

        # Check manifests
        assert len(manifests) == 2
        assert all("path" in m for m in manifests)
        assert all("size_bytes" in m for m in manifests)


def test_write_to_gcs(storage_client: StorageClient, mocker: "MockerFixture") -> None:
    """Test writing files to GCS."""
    # Mock GCS client
    mock_bucket = mocker.Mock()
    mock_blob = mocker.Mock()
    mock_bucket.blob.return_value = mock_blob
    
    mock_gcs_client = mocker.Mock()
    mock_gcs_client.bucket.return_value = mock_bucket
    storage_client._gcs_client = mock_gcs_client

    files = {
        "package.json": '{"name": "test"}',
        "src/index.ts": "console.log('test');",
    }

    manifests = storage_client._write_to_gcs("test-bucket", "output", files)

    # Check blobs were uploaded
    assert mock_blob.upload_from_string.call_count == 2
    assert len(manifests) == 2


def test_get_file_description(storage_client: StorageClient) -> None:
    """Test file description generation."""
    assert "Node.js" in storage_client._get_file_description("package.json")
    assert "TypeScript" in storage_client._get_file_description("tsconfig.json")
    assert "Docker" in storage_client._get_file_description("Dockerfile")
    assert "resolver" in storage_client._get_file_description(
        "src/resolvers/query.ts"
    )

