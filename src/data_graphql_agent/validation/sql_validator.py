"""BigQuery SQL validator using dry-run."""

from typing import List
from google.cloud import bigquery

from ..models.request_models import QueryInput


class SQLValidator:
    """Validates BigQuery SQL queries using dry-run API."""

    def __init__(self, project_id: str):
        """Initialize SQL validator.

        Args:
            project_id: Google Cloud Project ID
        """
        self.project_id = project_id
        self.client = bigquery.Client(project=project_id)

    async def validate_queries(self, queries: List[QueryInput]) -> List[str]:
        """Validate BigQuery SQL queries using dry-run.

        Args:
            queries: List of query inputs to validate

        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []

        for query in queries:
            try:
                # Run dry-run to validate SQL without executing
                job_config = bigquery.QueryJobConfig(
                    dry_run=True, use_query_cache=False
                )
                self.client.query(query.sql, job_config=job_config)

                # If we get here, the query is valid
            except Exception as e:
                errors.append(
                    f"Invalid SQL in query '{query.query_name}': {str(e)}"
                )

        return errors

    def validate_single_query(self, sql: str) -> tuple[bool, str]:
        """Validate a single SQL query.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            self.client.query(sql, job_config=job_config)
            return True, ""
        except Exception as e:
            return False, str(e)

