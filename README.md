# PDF Intelligence with Knowledge Graph and RAG

This system extracts information from PDF documents, builds a knowledge graph in Neo4j, and provides a natural language query interface. It leverages RAG (Retrieval-Augmented Generation) techniques to answer questions about the PDF content.

## Features

- **PDF Document Processing**: Loads and processes PDF files from a specified directory
- **Link Extraction**: Downloads and cleans linked external documents
- **Image Extraction**: Extracts images from PDFs and generates descriptions using LLaVA
- **External Document Retrieval**: Fetches and processes linked external documents
- **Knowledge Graph Creation**: Builds a knowledge graph in Neo4j from document content
- **Natural Language Queries**: Allows querying the knowledge graph using natural language
- **Chain-of-Thought Reasoning**: Performs step-by-step reasoning to generate accurate answers


## System Architecture

The system combines several components:
- **LLM**: Local LLM via Ollama for text generation (`llama2` by default)
- **Embedding Model**: Embedding model via Ollama for text vectorization (`bge-m3` by default)
- **Vision Language Model**: Vision model via Ollama for image description (`llava` by default)
- **Neo4j**: Graph database for knowledge graph storage (supports Neo4j Aura)
- **Redis**: Optional caching for improved performance
- **LlamaIndex**: Framework for document indexing and retrieval
- **Pydantic**: Configuration validation and management

## Prerequisites

- Python 3.9+
- Poetry (Python dependency management)
- Ollama running locally with the following models:
  - `llama2` (or alternative specified in config)
  - `bge-m3` (or alternative embedding model)
  - `llava` (for image processing)
- Neo4j database (compatible with Neo4j Aura cloud service)

## Installation

1. Clone the repository
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies using Poetry
```bash
# Install Poetry if you don't have it already
# pip install poetry

# Install project dependencies
poetry install
```

3. Configure your environment (see Configuration section)

4. Start Ollama with required models
```bash
# Ensure models specified in config.py are available in Ollama
```

5. Ensure Neo4j is running
```bash
# Neo4j should be accessible at the URL specified in config.py
```

## Configuration
```bash
# Optional: Pull Ollama models if not already downloaded
ollama pull llama2
ollama pull bge-m3
ollama pull llava
```

The project uses Pydantic for configuration management with validation. The settings are defined in `config.py` and can be customized through environment variables.

### Default Configuration

```python
# Neo4j Configuration
NEO4J_URI = "neo4j+s://<id>>.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "..."  # Credentials omitted for security
AURA_INSTANCEID = "<id>>"
AURA_INSTANCENAME = "Instance02"

# Redis Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PASSWORD = ""
REDIS_USERNAME = ""

# Directory Configuration
DOC_DIR = "input-dir"
DOWNLOAD_DOC_DIR = "download-dir"

# Ollama Configuration
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434
OLLAMA_LLM_MODEL = "llama2"  # Large Language Model
OLLAMA_EMBED_MODEL = "bge-m3"  # Embedding Model
OLLAMA_VLM_MODEL = "llava"  # Vision Language Model
```

### Customizing Configuration

You can override these settings by setting environment variables with the same names. For example:

```bash
# Set custom Ollama model
export OLLAMA_LLM_MODEL=deepseek-r1:14b

# Set custom directories
export DOC_DIR=my-documents
export DOWNLOAD_DOC_DIR=my-downloads

# Run the application
poetry run python main.py
```

### Configuration Validation

The configuration uses Pydantic validators to ensure:
- All port numbers are valid
- Neo4j URI has a valid format
- All string values contain only allowed characters
- Redis configuration is valid

## Directory Structure

```
├── pyproject.toml              # Poetry configuration
├── poetry.lock                 # Poetry lock file
├── README.md                   # This documentation file
├── config.py                   # Configuration settings
├── main.py                     # Main application file
├── query_part_only.py          # Script for just the query interface
├── basicneo4j.py               # Neo4j utilities
├── metadata.json               # Project metadata
├── nest_asyncio                # Asyncio patch for Jupyter
├── .gitignore                  # Git ignore file
├── devcontainer/               # Development container configuration
│   └── .link_cache             # Link cache for dev container
├── download-dir/               # Downloaded external documents
│   ├── linked_clean/           # Preprocessed documents
│   └── linked_raw/             # Raw downloaded documents
├── helper/                     # Helper utilities
│   ├── util_doc_helper.py      # Document processing utilities
│   ├── util_image_helper.py    # Image extraction and description utilities
│   └── util_link_helper.py     # Link extraction and processing utilities
├── input-dir/                  # Input PDF documents
│   └── sap-hana-on-vmware-vsp  # Example document
├── output-images/              # Extracted images from PDFs
└── prompt_templates/           # LLM prompt templates
    ├── cot_prompt_template.py  # Chain-of-thought prompt template
    └── image_prompt_template.py # Image description prompt template
```

## Usage

- `main.py`: Full pipeline — builds knowledge graph, processes images/links, and starts query session.
- `query_part_only.py`: Only loads the Neo4j knowledge graph and allows querying.

1. Place your PDF files in the `input-dir` directory

2. Run the main script using Poetry:
```bash
poetry run python main.py
```

3. To run only the query generation part:
```bash
poetry run python query_part_only.py
```

4. The system will:
   - Load and process PDF documents
   - Extract and store links in Neo4j
   - Fetch external linked documents
   - Extract and describe images
   - Build a knowledge graph in Neo4j
   - Start an interactive query session

5. When prompted, enter natural language questions about the content of your documents

## Example Queries

```
What are the main topics covered in these files?
What is the relationship between [concept1] and [concept2]?
Summarize the information about [specific topic]
```

## Helper Modules

### util_doc_helper.py
Contains functions for processing and extracting content from documents.

### util_image_helper.py
Contains functions for extracting images from PDFs and generating descriptions using LLaVA.

### util_link_helper.py
Contains functions for extracting links from PDFs, updating Neo4j with link information, and fetching/preprocessing external documents.

## Chain-of-Thought (CoT) Reasoning

The system uses a chain-of-thought prompt template to guide the LLM in generating well-reasoned responses. This improves the quality and accuracy of answers by encouraging step-by-step reasoning.

## Troubleshooting

- **Image Extraction Issues**: Ensure you have the required libraries for PDF processing
- **Ollama Connection Errors**: Verify Ollama is running and accessible at the specified host/port
- **Neo4j Connection Errors**: Check Neo4j credentials and ensure the database is running
- **Memory Issues**: For large document sets, consider processing in smaller batches

