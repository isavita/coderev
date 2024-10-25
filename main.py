import os
import sys
import click
import git
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from litellm import completion
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from pathlib import Path
import json
import re

# Constants
DEFAULT_MODEL = "ollama/qwen2.5-coder:7b-instruct-q5_K_M"
DEFAULT_TEMPERATURE = 0.0
CONFIG_FILENAME = ".codify.config"
DEFAULT_BASE_BRANCHES = ["main", "master"]

class ReviewMode(Enum):
    NORMAL = "normal"
    SECURITY = "security"
    PERFORMANCE = "performance"

@dataclass
class Config:
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    review_mode: ReviewMode = ReviewMode.NORMAL
    base_branch: str = "main"

    def to_dict(self):
        return {
            "model": self.model,
            "temperature": self.temperature,
            "review_mode": self.review_mode.value,
            "base_branch": self.base_branch
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            model=data.get("model", DEFAULT_MODEL),
            temperature=data.get("temperature", DEFAULT_TEMPERATURE),
            review_mode=ReviewMode(data.get("review_mode", "normal")),
            base_branch=data.get("base_branch", "main")
        )

class GitHandler:
    def __init__(self, repo_path: str = "."):
        try:
            self.repo = git.Repo(repo_path)
        except git.InvalidGitRepositoryError:
            raise click.ClickException("Not a git repository")

    def get_current_branch(self) -> str:
        return self.repo.active_branch.name

    def get_default_base_branch(self) -> str:
        """Detect the default base branch (main or master)"""
        for base in DEFAULT_BASE_BRANCHES:
            if base in self.repo.heads:
                return base
        raise click.ClickException(
            f"No default base branch found. Expected one of: {', '.join(DEFAULT_BASE_BRANCHES)}"
        )

    def get_branch_diff(self, branch_name: str, base_branch: Optional[str] = None) -> str:
        """Get diff between specified branch and base branch"""
        try:
            if base_branch is None:
                base_branch = self.get_default_base_branch()

            if branch_name == base_branch:
                raise click.ClickException(
                    f"Cannot compare {branch_name} with itself. "
                    "Please specify a different branch to review."
                )

            # Ensure both branches exist
            if branch_name not in self.repo.heads:
                raise click.ClickException(f"Branch '{branch_name}' not found")
            if base_branch not in self.repo.heads:
                raise click.ClickException(f"Base branch '{base_branch}' not found")

            # Get the diff between the branches
            diff = self.repo.git.diff(f"{base_branch}...{branch_name}")
            
            if not diff:
                raise click.ClickException(
                    f"No changes found between {branch_name} and {base_branch}"
                )
            
            return diff
        except git.GitCommandError as e:
            raise click.ClickException(f"Git error: {str(e)}")
        except Exception as e:
            raise click.ClickException(f"Error getting diff: {str(e)}")

    def list_branches(self) -> List[str]:
        """List all branches in the repository"""
        return [branch.name for branch in self.repo.heads]

class CodeReviewer:
    def __init__(self, repo_path: str = ".", debug: bool = False):
        self.git = GitHandler(repo_path)
        self.console = Console()
        self.debug = debug or os.getenv("CODIFY_DEBUG_ENABLED", "false").lower() == "true"
        self.config = self._load_config()

    def _load_config(self) -> Config:
        config_path = Path(self.git.repo.working_dir) / CONFIG_FILENAME
        if not config_path.exists():
            return Config()
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            return Config.from_dict(data)
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load config file: {e}[/]")
            return Config()

    def _save_config(self):
        config_path = Path(self.git.repo.working_dir) / CONFIG_FILENAME
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as e:
            raise click.ClickException(f"Error saving config: {str(e)}")

    def _debug_print(self, title: str, content: str):
        if self.debug:
            self.console.print(Panel(
                Syntax(content, "python", theme="monokai"),
                title=f"[blue]{title}[/]",
                border_style="blue"
            ))
    
    def _format_review_content(self, content: str) -> str:
        """Format the review content for display"""
        try:
            content = content.strip()
            
            # Find JSON content within code blocks if it exists
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            json_match = re.search(json_pattern, content, re.DOTALL)
            
            if json_match:
                try:
                    # Extract and parse the JSON content
                    json_content = json_match.group(1)
                    data = json.loads(json_content)
                    # Extract the actual review text from the JSON response
                    content = data.get('response', json_content)
                except json.JSONDecodeError:
                    # If JSON parsing fails, use the original content
                    pass
            
            # Remove any remaining code block markers and cleanup
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
            
            return content
        except Exception as e:
            if self.debug:
                self.console.print(f"[yellow]Warning: Error formatting content: {str(e)}[/]")
            # Return original content if anything goes wrong
            return content

    def review_branch(self, branch_name: str, base_branch: Optional[str] = None, system_msg: Optional[str] = None) -> str:
        try:
            # If no base_branch specified, use the one from config or detect it
            if not base_branch:
                try:
                    base_branch = self.config.base_branch
                except AttributeError:
                    base_branch = self.git.get_default_base_branch()

            diff = self.git.get_branch_diff(branch_name, base_branch)
            
            # Add branch information to the user message
            branch_info = f"Reviewing changes in branch '{branch_name}' compared to '{base_branch}':\n\n"
            
            default_system_msg = (
                "You are an experienced code reviewer. Review the following code changes "
                "and provide constructive feedback. Focus on:"
                "\n- Code quality and best practices"
                "\n- Potential bugs and edge cases"
                "\n- Performance implications"
                "\n- Security concerns"
                "\nProvide your feedback in markdown format."
            )

            system_msg = system_msg or default_system_msg
            user_msg = branch_info + diff

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
            
            if self.debug:
                self._debug_print("Raw LLM Response", review_content)
            
            # Format the content for display
            formatted_content = self._format_review_content(review_content)
            
            # Additional cleanup for display
            formatted_content = formatted_content.strip()
            
            return formatted_content

        except click.ClickException as e:
            raise e
        except Exception as e:
            raise click.ClickException(f"Error during review: {str(e)}")

    def list_branches(self) -> None:
        """Display branches in a formatted table"""
        table = Table(title="Available Branches")
        table.add_column("Branch Name", style="cyan")
        table.add_column("Current", style="green")

        current_branch = self.git.get_current_branch()
        for branch in self.git.list_branches():
            is_current = "✓" if branch == current_branch else ""
            table.add_row(branch, is_current)

        self.console.print(table)

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
        click.echo("✨ Codify initialized successfully!")
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('branch_name', required=False)
@click.option('--base', help='Base branch to compare against (defaults to main/master)')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--model', help='Specify LLM model')
@click.option('--temperature', type=float, help='Set temperature for LLM')
@click.option('--system-msg', help='Custom system message for the LLM')
def review(branch_name: Optional[str], base: Optional[str], debug: bool, 
          model: Optional[str], temperature: Optional[float], system_msg: Optional[str]):
    """Review changes in a branch compared to base branch (default: main/master)"""
    try:
        reviewer = CodeReviewer(debug=debug)
        
        if model:
            reviewer.config.model = model
        if temperature is not None:
            reviewer.config.temperature = temperature

        if not branch_name:
            branch_name = reviewer.git.get_current_branch()
            click.echo(f"No branch specified, reviewing current branch: {branch_name}")

        review_content = reviewer.review_branch(branch_name, base, system_msg)
        click.echo("\n" + review_content)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command(name='list')
def list_branches():
    """List all branches"""
    try:
        reviewer = CodeReviewer()
        reviewer.list_branches()
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.group()
def config():
    """Manage Codify configuration"""
    pass

@config.command(name='set')
@click.argument('key')
@click.argument('value')
def config_set(key: str, value: str):
    """Set a configuration value"""
    try:
        reviewer = CodeReviewer()
        if hasattr(reviewer.config, key):
            setattr(reviewer.config, key, value)
            reviewer._save_config()
            click.echo(f"✓ Set {key}={value}")
        else:
            click.echo(f"Error: Unknown configuration key: {key}", err=True)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@config.command(name='get')
@click.argument('key')
def config_get(key: str):
    """Get a configuration value"""
    try:
        reviewer = CodeReviewer()
        if hasattr(reviewer.config, key):
            value = getattr(reviewer.config, key)
            click.echo(f"{key}={value}")
        else:
            click.echo(f"Error: Unknown configuration key: {key}", err=True)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

@config.command(name='list')
def config_list():
    """List all configuration values"""
    try:
        reviewer = CodeReviewer()
        config_dict = reviewer.config.to_dict()
        table = Table(title="Current Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in config_dict.items():
            table.add_row(key, str(value))
        
        reviewer.console.print(table)
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == '__main__':
    cli()