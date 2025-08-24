# LLM Integration and Content Processing

## Overview

This module integrates the GitHub Copilot LLM (via `gh copilot` CLI) for automatic extraction of entities and relationships from text, and stores the results in the SQLite database.

## Components

- `src/muleta-coginitiva/llm_client.py`: LLM client using GitHub Copilot CLI
- `src/muleta-coginitiva/content_processor.py`: Processes text, extracts entities/relations, and stores them in the DB

## Usage

- The LLM client uses the `gh copilot suggest` command to extract structured data from text.
- The content processor takes text input, calls the LLM, and inserts entities/relations into the database.

## Testing

- `api/tests/test_llm_client.py`: Mocks the CLI and validates LLM output parsing
- `api/tests/test_content_processor.py`: Validates that text input results in correct DB inserts

## Example

```python
from muleta-coginitiva.content_processor import ContentProcessor
processor = ContentProcessor()
result = processor.process_text("Texto de teste.")
```

## Environment
- Requires GitHub CLI (`gh`) and Copilot extension installed and authenticated
