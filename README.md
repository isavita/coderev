# Codify

An AI-powered code review tool that uses LLMs to provide intelligent feedback on your pull requests.

## Quick Start

```bash
pip install codify
codify init
codify review feature-branch
```

## Options and Configuration

All options can be set via CLI arguments or configured in `.codify.config`:

```bash
# Via CLI:
codify review feature-branch [options]
  --model "gpt-4o"                  # LLM model to use
  --temperature 0.2                 # Model temperature (0-1)
  --system-msg "..."               # Override system message
  --instructions "..."             # Override review guidelines
  --base main                      # Base branch for comparison
  -f, --files file1.py file2.py   # Review specific files
  --debug                         # Enable debug output

# Via config:
codify config set <key> <value>
  model            # Default: gpt-4o
  temperature      # Default: 0.0
  base_branch      # Default: main
  system_message   # LLM system message
  review_instructions  # Review guidelines
```

### Supported Models (via litellm)

```bash
# OpenAI (OPENAI_API_KEY)
--model gpt-4o
--model o1-mini

# Anthropic (ANTHROPIC_API_KEY)
--model claude-3-sonnet-20240320

# Mistral (MISTRAL_API_KEY)
--model mistral/mistral-large-latest

# Gemini (GEMINI_API_KEY)
--model gemini/gemini-1.5-pro-latest

# Local via Ollama
--model ollama/qwen2.5-coder
```

For more models, see [litellm's documentation](https://docs.litellm.ai/docs/).

### Example Uses

```bash
# Review current branch
codify review

# Review specific files
codify review -f src/main.py tests/test_main.py

# Custom review focus
codify review --instructions "Focus on testing coverage"
codify review --system-msg "Security-focused code reviewer"

# Persistent configuration
codify config set model gpt-4o
codify config set review_instructions "Check error handling"
```

## Environment Variables

- `OPENAI_API_KEY`: For OpenAI models
- `ANTHROPIC_API_KEY`: For Anthropic models
- `MISTRAL_API_KEY`: For Mistral models
- `GEMINI_API_KEY`: For Gemini models
- `CODIFY_DEBUG_ENABLED`: Enable debug mode

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

Apache License 2.0
