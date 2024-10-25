import os
import sys
import click
import git
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict
from litellm import completion
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from pathlib import Path

# Constants
DEFAULT_MODEL = "ollama/qwen2.5-coder:7b-instruct-q5_K_M"
DEFAULT_TEMPERATURE = 0.0
CONFIG_FILE = ".codify.config"

class ReviewMode(Enum):
    NORMAL = "normal"
    SECURITY = "security"
    PERFORMANCE = "performance"

@dataclass
class Config:
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    review_mode: ReviewMode = ReviewMode.NORMAL

class CodeReviewer:
    def __init__(self, repo_path: str = ".", debug: bool = False):
        self.repo = git.Repo(repo_path)
        self.console = Console()
        self.debug = debug or os.getenv("CODIFY_DEBUG_ENABLED", "false").lower() == "true"
        self.config = self._load_config()

    def _load_config(self) -> Config:
        config_path = Path(self.repo.working_dir) / CONFIG_FILE
        if not config_path.exists():
            return Config()
        # TODO: Implement config file loading
        return Config()

    def _save_config(self):
        config_path = Path(self.repo.working_dir) / CONFIG_FILE
        # TODO: Implement config file saving
        pass

    def _debug_print(self, title: str, content: str):
        if self.debug:
            self.console.print(Panel(
                Syntax(content, "python", theme="monokai"),
                title=title,
                border_style="blue"
            ))

    def get_pr_diff(self, pr_number: int) -> str:
        # For local implementation, we'll use branch comparison
        # TODO: Implement proper PR diff retrieval
        return "Sample diff content"

    def review_pr(self, pr_number: int, system_msg: Optional[str] = None) -> str:
        diff = self.get_pr_diff(pr_number)
        
        default_system_msg = (
            "You are an experienced code reviewer. Review the following code changes "
            "and provide constructive feedback. Focus on:"
            "\n- Code quality and best practices"
            "\n- Potential bugs and edge cases"
            "\n- Performance implications"
            "\n- Security concerns"
        )

        system_msg = system_msg or default_system_msg
        user_msg = f"Please review the following code changes:\n\n{diff}"

        self._debug_print("System Message", system_msg)
        self._debug_print("User Message", user_msg)

        response = completion(
            model=self.config.model,
            temperature=self.config.temperature,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )

        review_content = response.choices[0].message.content
        self._debug_print("LLM Response", review_content)
        return review_content

    def list_prs(self) -> List[Dict]:
        # For local implementation, we'll list branches
        branches = [branch.name for branch in self.repo.heads]
        # TODO: Implement proper PR listing
        return [{"number": i, "branch": branch} for i, branch in enumerate(branches, 1)]

@click.group()
def cli():
    """Codify - AI-powered code review tool"""
    pass

@cli.command()
def init():
    """Initialize Codify in the current repository"""
    try:
        reviewer = CodeReviewer()
        reviewer._save_config()
        click.echo("Codify initialized successfully!")
    except git.InvalidGitRepositoryError:
        click.echo("Error: Not a git repository", err=True)

@cli.command()
@click.argument('pr_number', type=int)
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--model', help='Specify LLM model')
@click.option('--temperature', type=float, help='Set temperature for LLM')
@click.option('--system-msg', help='Custom system message for the LLM')
def review(pr_number: int, debug: bool, model: Optional[str],
          temperature: Optional[float], system_msg: Optional[str]):
    """Review a specific pull request"""
    reviewer = CodeReviewer(debug=debug)
    
    if model:
        reviewer.config.model = model
    if temperature is not None:
        reviewer.config.temperature = temperature

    try:
        review_content = reviewer.review_pr(pr_number, system_msg)
        click.echo(review_content)
    except Exception as e:
        click.echo(f"Error reviewing PR: {str(e)}", err=True)

@cli.command(name='list-prs')
def list_prs():
    """List all open pull requests"""
    reviewer = CodeReviewer()
    try:
        prs = reviewer.list_prs()
        for pr in prs:
            click.echo(f"PR #{pr['number']}: {pr['branch']}")
    except Exception as e:
        click.echo(f"Error listing PRs: {str(e)}", err=True)

@cli.group()
def config():
    """Manage Codify configuration"""
    pass

@config.command(name='set')
@click.argument('key')
@click.argument('value')
def config_set(key: str, value: str):
    """Set a configuration value"""
    reviewer = CodeReviewer()
    # TODO: Implement config setting
    click.echo(f"Set {key}={value}")

@config.command(name='get')
@click.argument('key')
def config_get(key: str):
    """Get a configuration value"""
    reviewer = CodeReviewer()
    # TODO: Implement config getting
    click.echo(f"Value for {key}")

if __name__ == '__main__':
    cli()