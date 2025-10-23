# Data GraphQL Agent

MCP (Model Context Protocol) agent that generates production-ready Apollo GraphQL servers from BigQuery SQL queries with Dataplex lineage tracking.

## Features

- 🚀 **Auto-generate Apollo GraphQL Servers** from BigQuery queries
- 📊 **BigQuery Integration** with type inference from SQL schemas
- 📝 **Dataplex Lineage Tracking** for end-to-end data governance
- 🐳 **Docker Support** for containerized deployments
- 🧪 **Test Client Generation** for API validation
- 🔌 **MCP Protocol** for seamless integration with Cursor and other AI assistants

## How It Works

### End-to-End Flow

```
1. Input         →  2. Schema Inference  →  3. Code Generation  →  4. Validation  →  5. Output
BigQuery SQL        Dry-run Analysis        Jinja2 Templates       Multi-level      GCS/Local
Queries             Type Mapping            Apollo Server v4       Checks           Files
```

**Detailed Steps:**

1. **Input**: You provide BigQuery SQL queries via MCP tool
2. **Schema Inference**: Agent runs BigQuery dry-run to infer result types
3. **Code Generation**: Generates complete Apollo Server project with templates
4. **Validation** (optional): Validates generated code at selected level
5. **Output**: Writes validated code to GCS or local filesystem
6. **Deployment**: You run the generated Node.js application

### Validation Levels

Choose validation thoroughness based on your needs:

| Level | Time | Coverage | Checks | Use Case |
|-------|------|----------|--------|----------|
| **Quick** | ~1s | 80% | GraphQL syntax, SQL dry-run, file structure | Rapid iteration, development |
| **Standard** | ~10s | 95% | Quick + TypeScript compilation, imports | Default, balanced approach |
| **Full** | ~60s | 99% | Standard + Docker build, server startup, health check | Pre-production, CI/CD |

## Architecture

The agent generates a complete TypeScript/Node.js project with:

- **Apollo Server v4** - GraphQL API server with plugins and context
- **Type-safe resolvers** - Auto-generated from BigQuery schemas
- **Dataplex integration** - Runtime lineage event tracking
- **Error handling** - Production-safe error formatting
- **Docker configuration** - Multi-stage builds for production
- **Test suite** - Integration tests and test client

## Installation

### Prerequisites

- Python 3.10-3.12
- Poetry (Python dependency management)
- Google Cloud account with BigQuery access

### Setup

```bash
# Clone the repository
git clone https://github.com/opendedup/data-graphql-agent.git
cd data-graphql-agent

# Install dependencies
poetry install

# Configure environment variables
cp .env.example .env
# Edit .env with your GCP credentials
```

## Configuration

Create a `.env` file or set environment variables:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1

# Output Configuration
GRAPHQL_OUTPUT_DIR=gs://your-bucket/graphql-server
# Or local path: GRAPHQL_OUTPUT_DIR=/path/to/output

# MCP Server Configuration
MCP_TRANSPORT=stdio  # or http
MCP_HOST=0.0.0.0
MCP_PORT=8080
```

## Usage

### As MCP Server (Recommended)

Configure in Cursor's `mcp.json`:

```json
{
  "mcpServers": {
    "data-graphql-agent": {
      "command": "poetry",
      "args": ["run", "python", "-m", "data_graphql_agent.mcp"],
      "cwd": "/path/to/data-graphql-agent",
      "env": {
        "GCP_PROJECT_ID": "your-project",
        "GRAPHQL_OUTPUT_DIR": "gs://your-bucket/graphql-server"
      }
    }
  }
}
```

### Direct Python Usage

```python
from data_graphql_agent.generation import ProjectGenerator
from data_graphql_agent.clients import StorageClient
from data_graphql_agent.models import QueryInput

# Define queries
queries = [
    QueryInput(
        query_name="trendingItems",
        sql="SELECT item, SUM(sales) as total FROM `project.dataset.sales` GROUP BY item",
        source_tables=["project.dataset.sales"]
    )
]

# Generate project
generator = ProjectGenerator(project_id="your-project")
files = generator.generate_project("my-project", queries)

# Write to storage
storage = StorageClient(project_id="your-project")
manifests = storage.write_files("gs://bucket/output", files)
```

### Running as HTTP Server

```bash
# Set transport to HTTP
export MCP_TRANSPORT=http
export MCP_PORT=8080

# Start server
poetry run python -m data_graphql_agent.mcp
```

Then call tools via HTTP:

```bash
curl -X POST http://localhost:8080/mcp/call-tool \
  -H "Content-Type: application/json" \
  -d '{
    "name": "generate_graphql_api",
    "arguments": {
      "queries": [...],
      "project_name": "my-project"
    }
  }'
```

## MCP Tools

### `generate_graphql_api`

Generates a complete Apollo GraphQL Server project with validation.

**Input:**
- `queries`: Array of query objects with `queryName`, `sql`, and `source_tables`
- `project_name`: Project name for lineage tracking
- `output_path`: Optional output location (defaults to GRAPHQL_OUTPUT_DIR)
- `validation_level`: Optional validation thoroughness - `"quick"`, `"standard"` (default), or `"full"`
- `auto_fix`: Optional boolean to attempt automatic error fixes (default: `false`)

**Output:**
- Complete TypeScript/Node.js project
- Docker configuration
- Test client
- Integration tests
- Validation results with checks passed and warnings

**Example with Validation:**

```python
result = await handle_generate_graphql_api({
    "queries": [
        {
            "queryName": "salesByRegion",
            "sql": "SELECT region, SUM(amount) as total FROM `project.dataset.sales` GROUP BY region",
            "source_tables": ["project.dataset.sales"]
        }
    ],
    "project_name": "analytics-api",
    "output_path": "./output",
    "validation_level": "standard",  # Quick validation for speed
    "auto_fix": false
})
```

**Success Response:**

```json
{
  "success": true,
  "output_path": "./output",
  "files_generated": [...],
  "message": "Successfully generated and validated Apollo GraphQL Server with 1 queries. Generated 15 files at ./output. Validation: 5 checks passed in 8.2s"
}
```

**Validation Failure Response:**

```json
{
  "success": false,
  "output_path": "./output",
  "files_generated": [],
  "message": "Code validation failed at standard level",
  "error": "Validation errors: Invalid SQL in query 'salesByRegion': Table not found; TypeScript compilation failed"
}
```

### `validate_graphql_schema`

Validates a GraphQL schema file.

**Input:**
- `schema_path`: Path to schema file

**Output:**
- Validation results with errors and warnings

## Generated Project Structure

```
graphql-server/
├── src/
│   ├── server.ts          # Main Apollo Server
│   ├── typeDefs.ts        # GraphQL schema
│   ├── resolvers.ts       # Query resolvers
│   └── lineage.ts         # Dataplex integration
├── test-client/           # Test client
├── tests/                 # Integration tests
├── package.json
├── tsconfig.json
├── Dockerfile
└── docker-compose.yml
```

## Running Generated Server

```bash
cd output/graphql-server

# Install dependencies
npm install

# Development mode
npm run dev

# Production build
npm run build
npm start

# Docker
docker-compose up --build
```

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run unit tests only
poetry run pytest tests/unit

# Run with coverage
poetry run pytest --cov=data_graphql_agent
```

### Code Formatting

```bash
# Format with Black
poetry run black src tests

# Lint with Ruff
poetry run ruff check src tests
```

## BigQuery Type Mapping

The agent automatically maps BigQuery types to GraphQL types:

| BigQuery Type | GraphQL Type |
|--------------|-------------|
| STRING | String |
| INT64 | Int |
| FLOAT64 | Float |
| BOOL | Boolean |
| TIMESTAMP/DATE | String (ISO 8601) |
| STRUCT | Custom Object Type |
| ARRAY | [Type] |

Nested structures (STRUCTs and ARRAYs) are fully supported with automatic type generation.

## Validation Benefits

### Why Validate Before Writing?

1. **Catch errors early** - Invalid SQL, type mismatches, and syntax errors detected before deployment
2. **Faster iteration** - No manual debugging of generated code
3. **Confidence** - Know your code will work before running `npm install`
4. **Cost savings** - Avoid wasted GCS writes and Docker builds for broken code
5. **CI/CD friendly** - Use `full` validation in pipelines for guaranteed deployments

### When to Use Which Level?

**Quick Validation (~1s)**
- ✅ Rapid prototyping and experimentation
- ✅ Iterating on SQL queries
- ✅ Testing query-to-schema mappings
- ❌ Not for production deployments

**Standard Validation (~10s)** - **Recommended Default**
- ✅ Normal development workflow
- ✅ Before committing to version control
- ✅ Balanced speed and thoroughness
- ✅ Most common use case

**Full Validation (~60s)**
- ✅ Pre-production deployments
- ✅ CI/CD pipelines
- ✅ Critical production updates
- ✅ When Docker compatibility is essential
- ❌ Too slow for rapid iteration

## Data Lineage

The generated GraphQL server automatically tracks data lineage in Google Cloud Dataplex:

- **Process**: Each resolver is registered as a process
- **Run**: Each query execution creates a run (with unique request ID)
- **Lineage Events**: Link BigQuery sources to BI report targets
- **Cleanup**: Graceful shutdown removes lineage processes

Lineage operations are asynchronous (fire-and-forget) and don't block API responses.

## License

Apache 2.0 - See [LICENSE](LICENSE) for details

## Contributing

Contributions are welcome! Please submit pull requests or open issues for bugs and feature requests.

