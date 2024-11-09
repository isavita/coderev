# Coderev

[![PyPI version](https://badge.fury.io/py/coderev.svg)](https://badge.fury.io/py/coderev)
[![Python versions](https://img.shields.io/pypi/pyversions/coderev.svg)](https://pypi.org/project/coderev/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

An AI-powered code review tool that uses LLMs to provide intelligent feedback on your pull requests.

- Supports multiple LLM providers (OpenAI, Anthropic, Gemini, Mistral)
- Seamless Git integration
- Customizable review focus and guidelines
- Command-line interface with persistent configuration

## Installation

```bash
pip install coderev
```

## Requirements

- Python ≥ 3.8
- Git repository
- One of the following:
  - OpenAI API key for GPT-4 models
  - Anthropic API key for Claude models
  - Mistral API key for Mistral models
  - Gemini API key for Google models
  - Local Ollama installation

## Quick Start

1. Initialize Coderev in your git repository:
```bash
coderev init
```

2. Set up your preferred LLM provider (e.g., OpenAI):
```bash
export OPENAI_API_KEY='your-api-key'
```

3. Review your changes:
```bash
coderev review
```

## Usage

### Basic Commands

```bash
# Review current branch
coderev review

# Review specific branch
coderev review feature/xyz

# Review specific files
coderev review -f src/main.py tests/test_main.py

# List available branches
coderev list
```

### Command Options

```bash
coderev review [OPTIONS] [BRANCH_NAME]

Options:
  --base-branch TEXT          Base branch for comparison (default: main/master)
  -f, --review-files FILE     Review specific files
  --model TEXT               LLM model to use (default: gpt-4o)
  --temperature FLOAT        Model temperature 0-1 (default: 0.0)
  --system-message TEXT      Custom system message/persona
  --review-instructions TEXT Custom review guidelines
  --debug                    Enable debug mode
  --help                     Show this message and exit
```

### Configuration

Configure defaults in `.coderev.config`:

```bash
# View configuration
coderev config list

# Set values
coderev config set model gpt-4o
coderev config set base_branch main
coderev config set temperature 0.0
coderev config set system_message "Custom reviewer persona"
coderev config set review_instructions "Custom review focus"
```

### Supported Models

Coderev uses [litellm](https://docs.litellm.ai/docs/) for model integration and supports:

- OpenAI models (requires `OPENAI_API_KEY`):
  - `gpt-4o` (recommended)
  - `o1-mini` (faster)

- Anthropic models (requires `ANTHROPIC_API_KEY`):
  - `claude-3-sonnet-20240320`

- Mistral models (requires `MISTRAL_API_KEY`):
  - `mistral/mistral-large-latest`

- Gemini models (requires `GEMINI_API_KEY`):
  - `gemini/gemini-1.5-pro-latest`

- Local models (requires Ollama):
  - `ollama/qwen2.5-coder`

### Environment Variables

| Variable | Description | Required For |
|----------|-------------|-------------|
| `OPENAI_API_KEY` | OpenAI API key | OpenAI models |
| `ANTHROPIC_API_KEY` | Anthropic API key | Claude models |
| `MISTRAL_API_KEY` | Mistral API key | Mistral models |
| `GEMINI_API_KEY` | Google API key | Gemini models |
| `CODEREV_DEBUG_ENABLED` | Enable debug mode | Debugging (optional) |

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/isavita/coderev
cd coderev

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run tests with coverage
pytest

# Run specific test
pytest tests/test_main.py -k test_name

# Run with debug output
pytest -vv
```

### Project Structure

```
coderev/
├── src/
│   └── coderev/
│       ├── __init__.py      # Package version and metadata
│       └── main.py          # Core functionality
├── tests/
│   ├── __init__.py
│   └── test_main.py        # Tests
├── setup.cfg               # Package metadata and config
├── pyproject.toml         # Build system requirements
└── README.md             # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Credits

- [litellm](https://github.com/BerriAI/litellm) - LLM provider integration
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
