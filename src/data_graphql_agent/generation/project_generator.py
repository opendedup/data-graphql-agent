"""Project generator that orchestrates all code generation."""

import os
from pathlib import Path
from typing import Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schema_generator import SchemaGenerator
from ..models.request_models import QueryInput


class ProjectGenerator:
    """Generates complete Apollo GraphQL Server project."""

    def __init__(self, project_id: str, gcp_location: str = "US"):
        """Initialize project generator.

        Args:
            project_id: Google Cloud Project ID
            gcp_location: Google Cloud Location/Region
        """
        self.project_id = project_id
        self.gcp_location = gcp_location
        self.schema_generator = SchemaGenerator(project_id)

        # Setup Jinja2 environment
        templates_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.jinja_env.filters["title"] = self._title_case

    def generate_project(
        self, 
        project_name: str, 
        queries: List[QueryInput],
        api_metadata: Optional[Dict[str, any]] = None
    ) -> Dict[str, str]:
        """Generate complete Apollo Server project.

        Args:
            project_name: Name of the project
            queries: List of query inputs
            api_metadata: Optional metadata about the API (insight, summary, etc.)

        Returns:
            Dictionary mapping file paths to file contents
        """
        files: Dict[str, str] = {}

        # Convert QueryInput models to dicts for template rendering
        query_dicts = [
            {
                "queryName": q.query_name,
                "sql": q.sql,
                "source_tables": q.source_tables,
                "description": q.description,
                "alignment_score": q.alignment_score,
                "iterations": q.iterations,
                "generation_time_ms": q.generation_time_ms,
                "validation_details": q.validation_details,
            }
            for q in queries
        ]

        # Generate GraphQL schema with metadata
        schema_text, field_schemas = self.schema_generator.generate_schema_from_queries(
            query_dicts, api_metadata
        )

        # Prepare template context
        context = {
            "project_name": project_name,
            "queries": query_dicts,
            "schema": schema_text,
        }

        # Generate root files
        files["package.json"] = self._render_template("package.json.j2", context)
        files["tsconfig.json"] = self._render_template("tsconfig.json.j2", context)
        files["Dockerfile"] = self._render_template("Dockerfile.j2", context)
        files["docker-compose.yml"] = self._render_template(
            "docker-compose.yml.j2", context
        )
        files["docker-compose.test.yml"] = self._render_template(
            "docker-compose.test.yml.j2", context
        )
        files[".dockerignore"] = self._render_template(".dockerignore.j2", context)
        files[".gitignore"] = self._render_template(".gitignore.j2", context)
        files["README.md"] = self._render_template("README.md.j2", context)

        # Generate source files
        files["src/server.ts"] = self._render_template("server.ts.j2", context)
        files["src/typeDefs.ts"] = self._render_template("typeDefs.ts.j2", context)
        files["src/resolvers.ts"] = self._render_template("resolvers.ts.j2", context)
        files["src/scalars.ts"] = self._render_template("scalars.ts.j2", context)
        files["src/context.ts"] = self._render_template("context.ts.j2", context)
        files["src/errors.ts"] = self._render_template("errors.ts.j2", context)

        # Generate test client
        files["test-client/package.json"] = self._render_template(
            "test-client-package.json.j2", context
        )
        files["test-client/tsconfig.json"] = self._render_template(
            "tsconfig.json.j2", context
        )
        files["test-client/src/client.ts"] = self._render_template(
            "test-client.ts.j2", context
        )
        files["test-client/src/run-tests.ts"] = self._render_template(
            "test-client-runner.ts.j2", context
        )

        # Generate .env.example
        files[".env.example"] = self._generate_env_example()
        
        # Generate .env with actual values
        files[".env"] = self._generate_env_file()

        # Generate integration test stubs
        files["tests/integration/test_server_startup.py"] = (
            self._generate_test_server_startup()
        )
        files["tests/integration/test_resolvers.py"] = self._generate_test_resolvers(
            query_dicts
        )
        files["tests/pytest.ini"] = self._generate_pytest_ini()

        return files

    def _render_template(self, template_name: str, context: Dict) -> str:
        """Render a Jinja2 template.

        Args:
            template_name: Name of template file
            context: Template context variables

        Returns:
            Rendered template string
        """
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    def _generate_env_example(self) -> str:
        """Generate .env.example file with actual project values.

        Returns:
            .env.example content
        """
        return f"""# BigQuery Configuration
BIGQUERY_PROJECT_ID={self.project_id}
BIGQUERY_LOCATION={self.gcp_location}

# Server Configuration
PORT=4000
NODE_ENV=development
"""

    def _generate_env_file(self) -> str:
        """Generate .env file with actual project values.
        
        This creates a working .env file for immediate use.

        Returns:
            .env content
        """
        return f"""# BigQuery Configuration
BIGQUERY_PROJECT_ID={self.project_id}
BIGQUERY_LOCATION={self.gcp_location}

# Server Configuration
PORT=4000
NODE_ENV=development
"""

    def _generate_test_server_startup(self) -> str:
        """Generate server startup test.

        Returns:
            Python test code
        """
        return '''"""Test server startup and health."""

import pytest
import requests
import time
import subprocess
import os
from typing import Generator

@pytest.fixture(scope="module")
def graphql_server() -> Generator[str, None, None]:
    """Start GraphQL server for testing."""
    # Start server using docker-compose
    env = os.environ.copy()
    env["BIGQUERY_PROJECT_ID"] = os.getenv("BIGQUERY_PROJECT_ID", "test-project")
    env["DATAPLEX_PROJECT_ID"] = os.getenv("DATAPLEX_PROJECT_ID", "test-project")
    
    proc = subprocess.Popen(
        ["docker-compose", "up", "--build"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for server to be ready
    url = "http://localhost:4000/graphql"
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code in (200, 400):  # GraphQL endpoint ready
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    
    yield url
    
    # Cleanup
    subprocess.run(["docker-compose", "down"])
    proc.terminate()


def test_server_starts(graphql_server: str) -> None:
    """Test that the GraphQL server starts successfully."""
    response = requests.get(graphql_server)
    assert response.status_code in (200, 400)  # 400 is expected for GET without query


def test_graphql_introspection(graphql_server: str) -> None:
    """Test GraphQL introspection query."""
    query = """
    query {
        __schema {
            queryType {
                name
            }
        }
    }
    """
    
    response = requests.post(
        graphql_server,
        json={"query": query},
        headers={"Content-Type": "application/json"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["__schema"]["queryType"]["name"] == "Query"
'''

    def _generate_test_resolvers(self, queries: List[Dict]) -> str:
        """Generate resolver tests.

        Args:
            queries: List of query dictionaries

        Returns:
            Python test code
        """
        test_code = '''"""Test GraphQL resolvers."""

import pytest
import requests
from typing import Generator


@pytest.fixture(scope="module")
def graphql_endpoint() -> str:
    """GraphQL endpoint URL."""
    return "http://localhost:4000/graphql"


def execute_graphql_query(endpoint: str, query: str) -> dict:
    """Execute a GraphQL query.
    
    Args:
        endpoint: GraphQL endpoint URL
        query: GraphQL query string
        
    Returns:
        Response JSON
    """
    response = requests.post(
        endpoint,
        json={"query": query},
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()


'''

        for query in queries:
            query_name = query["queryName"]
            test_code += f'''
def test_{query_name}(graphql_endpoint: str) -> None:
    """Test {query_name} resolver."""
    query = """
    query {{
        {query_name} {{
            # Add expected fields based on your schema
        }}
    }}
    """
    
    result = execute_graphql_query(graphql_endpoint, query)
    
    # Check for successful response
    assert "data" in result
    assert "{query_name}" in result["data"]
    
    # Add more specific assertions based on your data
'''

        return test_code

    def _generate_pytest_ini(self) -> str:
        """Generate pytest configuration.

        Returns:
            pytest.ini content
        """
        return """[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
"""

    def _title_case(self, value: str) -> str:
        """Convert string to title case for Jinja2 filter.

        Args:
            value: Input string

        Returns:
            Title cased string
        """
        return value.title().replace("_", "")

