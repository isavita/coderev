# Codify

An AI-powered code review tool that uses LLMs to provide intelligent feedback on your pull requests.

## Quick Start

```bash
pip install codify
codify init
codify review feature-branch
```

## Options and Configuration

All options can be set via CLI arguments and persisted in `.codify.config`:

### CLI Options

```bash
codify review [branch_name] [options]

Branch Selection:
  branch_name                      # Branch to review (optional, uses current if not specified)
  --base-branch BRANCH            # Base branch for comparison (default: main/master)

Review Scope:
  -f, --review-files FILE         # Review specific files (can be used multiple times)
  
LLM Configuration:
  --model MODEL                   # LLM model to use (default: gpt-4o)
  --temperature FLOAT            # Model temperature 0-1 (default: 0.0)

Review Customization:
  --system-message TEXT          # Override system message/persona
  --review-instructions TEXT     # Override review guidelines and focus

Debug:
  --debug                        # Enable debug output
```

### Configuration File

Configure default values in `.codify.config`:

```bash
# View current configuration
codify config list

# Set configuration values
codify config set <key> <value>

Available Keys:
  model                 # LLM model (default: gpt-4o)
  temperature          # Model temperature (default: 0.0)
  base_branch          # Default base branch (default: main)
  system_message       # Default system message/persona
  review_instructions  # Default review guidelines
```

### Supported Models (via litellm)

```bash
# OpenAI (OPENAI_API_KEY)
--model gpt-4o              # Recommended for complex reviews
--model o1-mini            # Faster, for simpler reviews

# Anthropic (ANTHROPIC_API_KEY)
--model claude-3-sonnet-20240320

# Mistral (MISTRAL_API_KEY)
--model mistral/mistral-large-latest

# Gemini (GEMINI_API_KEY)
--model gemini/gemini-1.5-pro-latest

# Local via Ollama
--model ollama/qwen2.5-coder  # No API key needed
```

For more models, see [litellm's documentation](https://docs.litellm.ai/docs/).

### Example Uses

```bash
# Basic Usage
codify review                     # Review current branch
codify review feature/xyz         # Review specific branch
codify review -f src/main.py      # Review specific file
codify review --base-branch dev   # Compare against different base

# Customizing Review Focus
codify review --review-instructions "Focus on:
- Test coverage and quality
- Error handling
- Performance implications"

# Customizing Reviewer Persona
codify review --system-message "You are a security-focused code reviewer..."

# Setting Persistent Defaults
codify config set model gpt-4o
codify config set review_instructions "Focus on code quality and testing"
codify config set base_branch develop
```

## Environment Variables

- `OPENAI_API_KEY`: For OpenAI models
- `ANTHROPIC_API_KEY`: For Anthropic models
- `MISTRAL_API_KEY`: For Mistral models
- `GEMINI_API_KEY`: For Gemini models
- `CODIFY_DEBUG_ENABLED`: Enable debug mode (set to "true")

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

Apache License 2.0
