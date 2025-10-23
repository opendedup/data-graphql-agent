# Quick Start Guide

Get started with the Data GraphQL Agent in 5 minutes.

## Prerequisites

- Python 3.10-3.12
- Poetry installed (`curl -sSL https://install.python-poetry.org | python3 -`)
- Google Cloud account with BigQuery access
- `gcloud` CLI authenticated

## Installation

```bash
# Clone or navigate to the project
cd /home/user/git/data-graphql-agent

# Install dependencies
poetry install

# Set up environment variables
export GCP_PROJECT_ID=your-project-id
export GRAPHQL_OUTPUT_DIR=./output
```

## Method 1: Cursor Integration (Recommended)

Add to your Cursor `mcp.json` file (`~/.cursor/mcp.json` or `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "data-graphql-agent": {
      "command": "poetry",
      "args": ["run", "python", "-m", "data_graphql_agent.mcp"],
      "cwd": "/home/user/git/data-graphql-agent",
      "env": {
        "GCP_PROJECT_ID": "your-project-id",
        "GRAPHQL_OUTPUT_DIR": "./output"
      }
    }
  }
}
```

Restart Cursor and use the MCP tools in your AI chat!

## Method 2: Direct Python Usage

```bash
# Run the example
poetry run python example_usage.py
```

This generates a sample GraphQL API in `./output/graphql-server/`

## Method 3: HTTP Server

```bash
# Start HTTP server
export MCP_TRANSPORT=http
export MCP_HOST=0.0.0.0
export MCP_PORT=8080
poetry run python -m data_graphql_agent.mcp
```

Then call the API:

```bash
curl -X POST http://localhost:8080/mcp/call-tool \
  -H "Content-Type: application/json" \
  -d '{
    "name": "generate_graphql_api",
    "arguments": {
      "queries": [
        {
          "queryName": "exampleQuery",
          "sql": "SELECT * FROM `your-project.dataset.table` LIMIT 10",
          "source_tables": ["your-project.dataset.table"]
        }
      ],
      "project_name": "my-project",
      "output_path": "./output"
    }
  }'
```

## Using the Generated GraphQL Server

After generation, your Apollo GraphQL server is ready:

```bash
# Navigate to generated server
cd output/graphql-server

# Install Node.js dependencies
npm install

# Create .env file with your credentials
cat > .env <<EOF
BIGQUERY_PROJECT_ID=your-project-id
BIGQUERY_LOCATION=US
DATAPLEX_PROJECT_ID=your-project-id
DATAPLEX_LOCATION=us-central1
PORT=4000
EOF

# Run in development mode
npm run dev

# Or build and run in production mode
npm run build
npm start
```

The GraphQL API will be available at `http://localhost:4000/graphql`

## Using Docker

```bash
cd output/graphql-server

# Build and run with Docker Compose
docker-compose up --build

# Access the API
open http://localhost:4000/graphql
```

## Example Query

Once your server is running, try this in the GraphQL Playground:

```graphql
query {
  exampleQuery {
    # Your fields here based on the BigQuery schema
  }
}
```

## Testing Your API

The generated server includes a test client:

```bash
cd output/graphql-server/test-client
npm install
npm test
```

## Troubleshooting

### Authentication Error

```bash
# Authenticate with Google Cloud
gcloud auth application-default login
```

### No Such Table Error

Make sure your BigQuery table exists and you have access:

```bash
bq show your-project:dataset.table
```

### Port Already in Use

Change the port in the generated `.env` file:

```bash
PORT=4001
```

## Next Steps

1. **Customize the generated code** - Edit resolvers, add authentication, etc.
2. **Deploy to Cloud Run** - See deployment instructions in the generated README
3. **Add more queries** - Re-run the generator with additional queries
4. **Monitor lineage** - Check Dataplex for data lineage events

## Support

- See `README.md` for complete documentation
- See `IMPLEMENTATION_SUMMARY.md` for technical details
- Run tests: `poetry run pytest tests/unit -v`

## Example with Real Data

Here's a complete example with a real BigQuery public dataset:

```python
from data_graphql_agent.mcp.handlers import handle_generate_graphql_api
import asyncio

async def generate():
    result = await handle_generate_graphql_api({
        "queries": [
            {
                "queryName": "popularBabyNames",
                "sql": """
                    SELECT name, gender, SUM(number) as total
                    FROM `bigquery-public-data.usa_names.usa_1910_current`
                    WHERE year >= 2020
                    GROUP BY name, gender
                    ORDER BY total DESC
                    LIMIT 10
                """,
                "source_tables": ["bigquery-public-data.usa_names.usa_1910_current"]
            }
        ],
        "project_name": "baby-names-api",
        "output_path": "./output/baby-names-server"
    })
    print(result)

asyncio.run(generate())
```

This creates a complete GraphQL API for querying popular baby names!

