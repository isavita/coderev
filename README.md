# Codify

An AI-powered code review tool that uses LLMs to provide intelligent feedback on your pull requests.

## Installation

```bash
pip install codify
```

## Quick Start

```bash
# Initialize in your git repository
codify init

# Review current branch
codify review

# Review specific branch or files
codify review feature-branch
codify review -f file1.py file2.py

# Custom review instructions
codify review --system-msg "Focus on security aspects"
```

## Supported Models

Codify uses `litellm` for model integration and supports various LLM [providers](https://docs.litellm.ai/docs/providers). The default model is `gpt-4o`.

Examples:
```bash
# OpenAI (requires OPENAI_API_KEY)
codify review --model gpt-4o
codify review --model o1-mini

# Anthropic (requires ANTHROPIC_API_KEY)
codify review --model claude-3-sonnet-20240320

# Mistral (requires MISTRAL_API_KEY)
codify review --model mistral/mistral-large-latest

# Gemini (requires GEMINI_API_KEY)
codify review --model gemini/gemini-1.5-pro-latest

# Local models via Ollama (requires Ollama installation)
codify review --model ollama/qwen2.5-coder
```

For a complete list of supported models and their required environment variables, see [litellm's documentation](https://docs.litellm.ai/docs/).

## Configuration

Manage settings in `.codify.config`:

```bash
# View settings
codify config list

# Model settings
codify config set model gpt-4o
codify config set temperature 0.2

# Review customization
codify config set system_message "Your custom review instructions"
```

Default configuration:
- Model: `gpt-4o`
- Temperature: 0.0
- System Message: General code review instructions focusing on quality and best practices

### Review Instructions

You can customize review instructions in three ways (in order of priority):
1. Command-line argument: `--system-msg "Custom instructions"`
2. Configuration file: `codify config set system_message "Default instructions"`
3. Built-in default focusing on code quality and best practices

Example customizations:
```bash
# Focus on security
codify review --system-msg "Focus on security vulnerabilities and best practices"

# Performance review
codify config set system_message "Analyze performance implications and optimization opportunities"
```

## Environment Variables

- `OPENAI_API_KEY`: For OpenAI models
- `ANTHROPIC_API_KEY`: For Anthropic models
- `MISTRAL_API_KEY`: For Mistral models
- `GEMINI_API_KEY`: For Gemini models
- `CODIFY_DEBUG_ENABLED`: Enable debug mode (set to "true")

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.