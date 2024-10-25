# Codify CLI

Codify is a command-line interface tool that leverages Large Language Models (LLMs) to perform automated code reviews on pull requests. It currently works with local git repositories and supports various LLM models through the `litellm` library.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/codify-cli
cd codify-cli
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Dependencies

Create a `requirements.txt` file with the following dependencies:
```
click>=8.0.0
gitpython>=3.1.0
litellm>=1.0.0
rich>=13.0.0
```

## Usage

### Basic Commands

1. Initialize Codify in your repository:
```bash
python main.py init
```

2. List all open pull requests (currently shows local branches):
```bash
python main.py list-prs
```

3. Review a specific pull request:
```bash
python main.py review <pr_number>
```

### Advanced Usage

1. Review with debug output:
```bash
python main.py review <pr_number> --debug
```

2. Review with a specific model:
```bash
python main.py review <pr_number> --model "ollama/qwen2.5-coder:7b-instruct-q5_K_M"
```

3. Adjust the LLM temperature:
```bash
python main.py review <pr_number> --temperature 0.5
```

4. Use a custom system message:
```bash
python main.py review <pr_number> --system-msg "Focus on security aspects"
```

### Configuration Management

1. Set a configuration value:
```bash
python main.py config set model "ollama/qwen2.5-coder:7b-instruct-q5_K_M"
```

2. Get a configuration value:
```bash
python main.py config get model
```

### Environment Variables

- `CODIFY_DEBUG_ENABLED`: Set to "true" to enable debug mode globally
```bash
export CODIFY_DEBUG_ENABLED=true
```

## Development Setup

1. Install development dependencies:
```bash
pip install pytest pytest-cov black isort
```

2. Run tests:
```bash
pytest tests/
```

3. Format code:
```bash
black .
isort .
```

## Project Structure

```
codify-cli/
├── main.py           # Main CLI implementation
├── requirements.txt  # Project dependencies
├── tests/           # Test directory
│   ├── __init__.py
│   └── test_main.py
└── README.md        # This file
```

## Configuration

Codify stores its configuration in a `.codify.config` file in your repository root. The default configuration includes:

- Model: `ollama/qwen2.5-coder:7b-instruct-q5_K_M`
- Temperature: 0.0
- Review Mode: normal

## Making it Executable

To make the CLI tool easier to use, you can:

1. Make the script executable (Unix-like systems):
```bash
chmod +x main.py
```

2. Create a symlink in your PATH:
```bash
ln -s /path/to/main.py /usr/local/bin/codify
```

Now you can use the tool simply by typing:
```bash
codify review 1
```

## Features

- [x] Local repository support
- [x] Basic PR review functionality
- [x] Debug mode with rich formatting
- [x] Configuration management
- [ ] GitHub API integration
- [ ] Review history tracking
- [ ] Custom review templates
- [ ] Diff parsing and formatting

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [litellm](https://github.com/BerriAI/litellm) for LLM integration
- [Click](https://click.palletsprojects.com/) for CLI interface
- [Rich](https://rich.readthedocs.io/) for terminal formatting