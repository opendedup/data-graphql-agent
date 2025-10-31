"""BigQuery view generator for GraphQL queries."""

import logging
import re
from typing import Dict, List
from google.cloud import bigquery

logger = logging.getLogger(__name__)


class ViewGenerator:
    """Generates BigQuery views from SQL queries."""

    def __init__(self, project_id: str, location: str = "US"):
        """Initialize view generator.

        Args:
            project_id: Google Cloud Project ID
            location: BigQuery location/region
        """
        self.project_id = project_id
        self.location = location
        self.client = bigquery.Client(project=project_id)

    def create_views_for_queries(
        self, project_name: str, queries: List[Dict[str, any]]
    ) -> Dict[str, str]:
        """Create BigQuery views for all queries.

        Args:
            project_name: GraphQL project name
            queries: List of query dictionaries with 'queryName' and 'sql'

        Returns:
            Dictionary mapping query names to view identifiers
        """
        # Determine dataset name from project name
        dataset_name = self._sanitize_dataset_name(project_name)
        
        # Create dataset if it doesn't exist
        self._ensure_dataset_exists(dataset_name)

        view_map = {}
        for query in queries:
            query_name = query["queryName"]
            sql = query["sql"]
            
            # Create view
            view_id = self._create_view(dataset_name, query_name, sql)
            view_map[query_name] = view_id
            logger.info(f"Created view: {view_id}")

        return view_map

    def _sanitize_dataset_name(self, project_name: str) -> str:
        """Sanitize project name for BigQuery dataset.

        Args:
            project_name: Raw project name

        Returns:
            Valid BigQuery dataset name (lowercase, alphanumeric + underscore)
        """
        # BigQuery dataset names: alphanumeric + underscores, max 1024 chars
        sanitized = project_name.lower().replace("-", "_").replace(" ", "_")
        # Remove invalid characters
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")
        # Add suffix
        return f"{sanitized}_graphql"

    def _ensure_dataset_exists(self, dataset_name: str) -> None:
        """Create BigQuery dataset if it doesn't exist.

        Args:
            dataset_name: Dataset name to create
        """
        dataset_id = f"{self.project_id}.{dataset_name}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = self.location
        dataset.description = f"Generated views for GraphQL API: {dataset_name}"

        try:
            dataset = self.client.create_dataset(dataset, exists_ok=True)
            logger.info(f"Dataset {dataset_id} ready (location: {self.location})")
        except Exception as e:
            logger.error(f"Failed to create dataset {dataset_id}: {e}")
            raise

    def _create_view(self, dataset_name: str, query_name: str, sql: str) -> str:
        """Create a BigQuery view from SQL query.

        Args:
            dataset_name: Dataset name
            query_name: Query name (used as view name)
            sql: SQL query defining the view

        Returns:
            Full view identifier (project.dataset.view)
        """
        view_name = self._sanitize_view_name(query_name)
        view_id = f"{self.project_id}.{dataset_name}.{view_name}"

        view = bigquery.Table(view_id)
        view.view_query = sql

        try:
            view = self.client.create_table(view, exists_ok=True)
            logger.info(f"Created view: {view_id}")
            return view_id
        except Exception as e:
            logger.error(f"Failed to create view {view_id}: {e}")
            raise

    def _sanitize_view_name(self, query_name: str) -> str:
        """Sanitize query name for BigQuery view.

        Args:
            query_name: Raw query name (camelCase)

        Returns:
            Valid BigQuery view name (snake_case, lowercase, alphanumeric + underscore)
        """
        # Convert camelCase to snake_case
        sanitized = re.sub(r'(?<!^)(?=[A-Z])', '_', query_name).lower()
        # Remove invalid characters
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")
        return sanitized

