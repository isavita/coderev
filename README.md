# Codify

Codify is a command-line tool that uses LLMs (Large Language Models) to perform automated code reviews. It works with local git repositories and leverages the `litellm` library to provide intelligent code review feedback.

## Installation

1. Clone and set up the repository:
```bash
git clone https://github.com/yourusername/codify
cd codify
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Commands

```bash
# Initialize Codify in your repository
python main.py init

# List all branches
python main.py list

# Review current branch changes
python main.py review

# Review specific branch
python main.py review feature-branch

# Review specific files
python main.py review --files path/to/file1.py path/to/file2.py
```

### Advanced Options

```bash
# Enable debug output
python main.py review --debug

# Use specific model
python main.py review --model "ollama/qwen2.5-coder:7b-instruct-q5_K_M"

# Compare against different base branch
python main.py review feature-branch --base develop
```

### Configuration

Codify stores its settings in `.codify.config`. Manage configuration with:

```bash
# Set configuration
python main.py config set model "ollama/qwen2.5-coder:7b-instruct-q5_K_M"

# List current configuration
python main.py config list
```

Default configuration:
- Model: `ollama/qwen2.5-coder:7b-instruct-q5_K_M`
- Temperature: 0.0
- Review Mode: normal

### Environment Variables

- `CODIFY_DEBUG_ENABLED`: Set to "true" to enable debug mode globally

## Making it Executable (Optional)

Make the tool easier to use by adding it to your PATH:

```bash
chmod +x main.py
ln -s /path/to/main.py /usr/local/bin/codify
```

Then use it as:
```bash
codify review
```

## License

This project is licensed under the MIT License.

## Acknowledgments

- [litellm](https://github.com/BerriAI/litellm) - LLM integration
- [Click](https://click.palletsprojects.com/) - CLI interface
- [Rich](https://rich.readthedocs.io/) - Terminal formatting