"""Example usage of Data GraphQL Agent.

This script demonstrates how to use the agent to generate a GraphQL API
from BigQuery queries.
"""

import asyncio
import os
from pathlib import Path

from data_graphql_agent.mcp.handlers import handle_generate_graphql_api


async def main() -> None:
    """Generate example GraphQL API."""
    # Define sample queries
    arguments = {
        "queries": [
            {
                "queryName": "trendingItems",
                "sql": """
                    SELECT 
                        item_name,
                        SUM(sales) as total_sales,
                        AVG(price) as avg_price
                    FROM `project.dataset.sales`
                    GROUP BY item_name
                    ORDER BY total_sales DESC
                    LIMIT 10
                """,
                "source_tables": ["project.dataset.sales"],
            },
            {
                "queryName": "salesByRegion",
                "sql": """
                    SELECT 
                        region,
                        DATE(sale_date) as date,
                        SUM(amount) as total_amount,
                        COUNT(*) as num_transactions
                    FROM `project.dataset.sales`
                    GROUP BY region, DATE(sale_date)
                    ORDER BY date DESC
                """,
                "source_tables": ["project.dataset.sales"],
            },
        ],
        "project_name": "example-analytics",
        "output_path": "./output/graphql-server",
    }

    print("Generating GraphQL API...")
    print(f"  Project: {arguments['project_name']}")
    print(f"  Queries: {len(arguments['queries'])}")
    print(f"  Output: {arguments['output_path']}\n")

    # Generate the API
    result = await handle_generate_graphql_api(arguments)

    # Print results
    if result["success"]:
        print("✓ Generation successful!")
        print(f"\nMessage: {result['message']}")
        print(f"\nGenerated files ({len(result['files_generated'])}):")
        for file_info in result["files_generated"]:
            size_kb = file_info["size_bytes"] / 1024
            print(f"  - {Path(file_info['path']).name}: {size_kb:.1f} KB")
        
        print("\n" + "="*60)
        print("Next steps:")
        print("="*60)
        print(f"1. cd {arguments['output_path']}")
        print("2. npm install")
        print("3. Set environment variables in .env file")
        print("4. npm run dev")
        print("\nOr use Docker:")
        print("  docker-compose up --build")
    else:
        print("✗ Generation failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    # Set required environment variable for example
    if not os.getenv("GCP_PROJECT_ID"):
        os.environ["GCP_PROJECT_ID"] = "example-project"

    asyncio.run(main())

