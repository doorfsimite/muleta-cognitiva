# LLM Integration and Content Processing

## Overview

This module integrates the Anthropic Claude API for automatic extraction of entities and relationships from text, and stores the results in the SQLite database.

## Components

- `src/api/llm_client.py`: LLM client using Anthropic API with local fallback
- `src/api/content_processor.py`: Processes text, extracts entities/relations, and stores them in the DB

## Configuration

### Environment Variables

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Supported Models

The client uses `claude-3-5-sonnet-20241022` by default, but can be configured to use other Anthropic models:

```python
client = LLMClient(model="claude-3-haiku-20240307")
```

## Usage

### Basic Usage

```python
from api.llm_client import LLMClient

# Initialize with environment variable
client = LLMClient()

# Or with explicit API key
client = LLMClient(api_key="your-key")

# Extract entities and relations
result = client.extract_entities_relations("Your text content here")
print(f"Found {len(result['entities'])} entities and {len(result['relations'])} relations")
```

### Content Processing

```python
from api.content_processor import ContentProcessor

processor = ContentProcessor()
result = processor.process_text("Texto de teste sobre conceitos filosóficos.")
```

## Features

### Entity Extraction

The system identifies and extracts:
- **Pessoas**: Names of individuals
- **Lugares**: Geographic locations and places
- **Organizações**: Companies, institutions, groups
- **Conceitos**: Abstract ideas and concepts
- **Teorias**: Theoretical frameworks
- **Eventos**: Historical or significant events
- **Obras**: Books, papers, artworks
- **Tecnologias**: Tools and technologies
- **Métodos**: Methodologies and approaches

### Relation Types

Supported relationship types between entities:
- **tipo_de**: Type/subtype relationships
- **parte_de**: Part-of relationships
- **exemplo_de**: Example relationships
- **causa_de**: Causal relationships
- **efeito_de**: Effect relationships
- **apoia**: Supporting relationships
- **contradiz**: Contradictory relationships
- **relacionado_a**: General associations

### Fallback Mechanism

When the Anthropic API is unavailable, the system falls back to:
1. **Rule-based extraction**: Identifies quoted phrases and capitalized words
2. **Heuristic relations**: Creates basic relationships between entities
3. **Graceful degradation**: Continues processing without external dependencies

## Error Handling

The LLM client provides robust error handling:

```python
from api.llm_client import LLMError

try:
    result = client.extract_entities_relations(text)
except LLMError as e:
    print(f"Extraction failed: {e}")
    # Handle fallback or error reporting
```

## Health Monitoring

Check the LLM client status:

```python
status = client.health_check()
print(f"Anthropic configured: {status['anthropic_configured']}")
print(f"API connectivity: {status['anthropic_connectivity']}")
```

## Testing

### Running Tests

```bash
# Run LLM client tests
uv run pytest src/tests/test_llm_client.py -v

# Run with coverage
uv run pytest src/tests/test_llm_client.py --cov=src/api/llm_client
```

### Test Coverage

The test suite covers:
- **Initialization**: Various configuration scenarios
- **Anthropic Integration**: API calls and response handling
- **Fallback Mechanisms**: Rule-based extraction
- **Error Scenarios**: API failures and invalid responses
- **Response Parsing**: JSON extraction from various formats
- **Health Checks**: Connectivity and status monitoring

### Mocking in Tests

For testing without API calls:

```python
from unittest.mock import patch, Mock

@patch('api.llm_client.anthropic')
def test_extraction(mock_anthropic):
    mock_client = Mock()
    mock_anthropic.Anthropic.return_value = mock_client
    
    # Configure mock response
    mock_message = Mock()
    mock_message.content = [Mock(type='text', text='{"entities": [], "relations": []}')]
    mock_client.messages.create.return_value = mock_message
    
    client = LLMClient(api_key="test")
    result = client.extract_entities_relations("test text")
```

## Performance Considerations

### API Rate Limits

The Anthropic API has rate limits. The client includes:
- **Request timeouts**: Configurable timeout (default 60s)
- **Error logging**: Detailed error tracking
- **Graceful degradation**: Fallback to local processing

### Prompt Optimization

The extraction prompt is optimized for:
- **Clarity**: Clear instructions in Portuguese
- **Structure**: Consistent JSON output format
- **Efficiency**: Minimal token usage while maintaining quality
- **Robustness**: Handles noisy input from OCR/audio

### Local Fallback Performance

The rule-based fallback is designed to be:
- **Fast**: Regex-based extraction with minimal processing
- **Reliable**: No external dependencies
- **Consistent**: Predictable output format

## Integration Points

### Database Integration

Extracted entities and relations are stored using:
- **Entity normalization**: Canonical naming and deduplication
- **Relationship validation**: Type checking and evidence tracking
- **Source attribution**: Links back to original content

### Web Interface

The web visualization consumes LLM-extracted data through:
- **REST API endpoints**: JSON-formatted entity/relation data
- **Real-time updates**: Automatic refresh after content processing
- **Interactive exploration**: Click-through navigation of relationships

### MCP Server Integration

The MCP server exposes LLM functionality as tools:
- **process_content**: Direct text processing
- **extract_entities**: Entity identification
- **generate_relations**: Relationship discovery

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```bash
   # Check environment variable
   echo $ANTHROPIC_API_KEY
   
   # Set if missing
   export ANTHROPIC_API_KEY="your-key"
   ```

2. **Connection Errors**
   ```python
   # Test connectivity
   status = client.health_check()
   if status['anthropic_connectivity'] != 'ok':
       print(f"Connection issue: {status['anthropic_connectivity']}")
   ```

3. **Invalid JSON Responses**
   - The client includes robust JSON parsing with fallbacks
   - Check logs for parsing warnings
   - Verify prompt formatting if using custom prompts

4. **Rate Limiting**
   - Implement retry logic in your application
   - Consider caching results for repeated content
   - Use fallback mode for development/testing

### Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# LLM client will log API calls and responses
client = LLMClient()
```

View recent processing results:

```python
# Check what was extracted from recent content
result = client.extract_entities_relations(text)
print(f"Entities: {[e['name'] for e in result['entities']]}")
print(f"Relations: {[(r['from'], r['type'], r['to']) for r in result['relations']]}")
```

## Future Enhancements

### Planned Features

1. **Multi-model Support**: Integration with additional LLM providers
2. **Streaming Processing**: Real-time processing for large documents
3. **Custom Prompts**: User-configurable extraction templates
4. **Quality Scoring**: Confidence metrics for extracted entities/relations
5. **Batch Processing**: Efficient processing of multiple documents

### Configuration Options

Future configuration capabilities:
- **Model Selection**: Choose between different Claude models
- **Temperature Control**: Adjust response randomness
- **Token Limits**: Configure response length limits
- **Custom Entity Types**: Define domain-specific entity categories
- **Relation Validation**: Custom relationship type validation

## API Reference

### LLMClient Class

```python
class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_to_local: bool = True,
        request_timeout: int = 60,
    )
    
    def extract_entities_relations(
        self,
        text: str,
        source_type: str = "text",
        source_path: Optional[str] = None
    ) -> Dict[str, Any]
    
    def health_check(self) -> Dict[str, Any]
```

### Response Format

```json
{
  "entities": [
    {
      "name": "Entity Name",
      "type": "conceito|pessoa|lugar|organizacao|...",
      "description": "Brief description in Portuguese"
    }
  ],
  "relations": [
    {
      "from": "Source Entity",
      "to": "Target Entity", 
      "type": "relacionado_a|tipo_de|parte_de|...",
      "evidence": "Supporting evidence or citation"
    }
  ]
}
```
