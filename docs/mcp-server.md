# MCP Server Implementation

## Overview

The MCP server (`src/api/mcp_server.py`) implements the Model Context Protocol (MCP) for tool discovery and invocation with complete API coverage. It supports:

- **Tool Registration**: Complete registry of all 19 API tools from the design specification
- **Protocol Compliance**: Full MCP protocol handling for tool discovery and invocation
- **Error Handling**: Robust error handling with proper logging
- **Type Safety**: Type hints and parameter validation
- **Async Support**: Full async/await implementation

## Architecture

### Tool Registry
- `ToolRegistry` class manages tool registration with metadata
- Each tool includes name, description, and parameter definitions
- Tools are automatically registered during server initialization

### MCP Protocol Support
- `tool_discovery`: Returns comprehensive list of available tools with metadata
- `invoke_tool`: Invokes tools with parameter validation and error handling
- JSON message parsing with proper error responses

## Registered Tools

The server implements 19 tools covering all API endpoints:

### Content Processing
- `process_content`: Process text content and extract entities
- `get_entities`: Retrieve all entities
- `get_entity`: Get specific entity with relations

### Spaced Repetition
- `get_due_cards`: Get cards due for review
- `generate_cards`: Generate spaced repetition cards
- `review_card`: Record card review and update scheduling

### Socratic Questioning
- `get_socratic_questions`: Generate Socratic questions for entities
- `generate_questions`: Generate questions with specific types

### Argument Flowcharts
- `get_arguments`: Get argument sequences
- `create_argument`: Create new argument flowchart
- `get_argument`: Get specific argument with nodes

### Assessments
- `get_assessments`: Get available assessments
- `create_assessment`: Create new assessment
- `get_assessment`: Get specific assessment with questions

### Knowledge Analysis
- `get_knowledge_gaps`: Identify knowledge gaps
- `get_knowledge_stats`: Get performance statistics

### Visualization & Export
- `get_visualization_data`: Get data for graph visualization
- `export_anki`: Export cards to Anki format
- `health_check`: Server health and connectivity check

## Usage

### Starting the Server
```sh
cd /Users/davisimite/Documents/muleta-cognitiva
uv run python src/api/mcp_server.py
```

### GitHub Copilot Integration
The server runs on `127.0.0.1:8765` and can be connected to GitHub Copilot for:
- Content processing automation
- Knowledge graph exploration
- Spaced repetition management
- Assessment creation

## Testing

### Test Coverage
Comprehensive test suite in `src/tests/test_mcp_server.py`:
- Tool discovery with metadata validation
- Tool invocation with parameter handling
- Error handling for invalid requests
- Protocol compliance verification

### Running Tests
```sh
uv run pytest src/tests/test_mcp_server.py -v
```

## Implementation Status

✅ **Step 3 Complete**: Basic MCP Server Implementation
- MCP protocol handling implemented
- All 19 API tools registered
- Comprehensive test coverage
- Server accepts connections and responds to tool discovery
- GitHub Copilot can connect and discover tools

### Next Steps
- Step 4: LLM Integration and Content Processing
- Database integration for tool implementations
- Real functionality behind placeholder tool handlers
