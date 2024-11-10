import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import git
from litellm import completion
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# Constants
DEFAULT_MODEL = "gpt-4o"
DEFAULT_BASE_BRANCH = "main"
DEFAULT_TEMPERATURE = 0.0
CONFIG_FILENAME = ".coderev.config"
DEFAULT_BASE_BRANCHES = ["main", "master"]
DEFAULT_SYSTEM_MESSAGE = (
    "You are an experienced code reviewer. Analyze the code changes and provide "
    "constructive feedback following the given guidelines. Format your response "
    "in markdown with clear sections for different types of findings. "
    "Be concise but thorough, focusing on impactful changes and potential issues."
)
DEFAULT_REVIEW_INSTRUCTIONS = """**Review Guidelines:**
1. **Focus Areas:**
  - Identify specific lines or sections that need attention
  - Evaluate code quality and adherence to best practices
  - Check for potential bugs and edge cases
  - Assess performance implications
  - Review security considerations

2. **Review Approach:**
  - Prioritize critical issues over minor style concerns
  - Highlight well-written code and effective solutions
  - Suggest improvements only when they add significant value
  - Be specific in your feedback and recommendations"""


@dataclass
class Config:
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    base_branch: str = DEFAULT_BASE_BRANCH
    system_message: str = DEFAULT_SYSTEM_MESSAGE
    review_instructions: str = DEFAULT_REVIEW_INSTRUCTIONS

    def to_dict(self):
        return {
            "model": self.model,
            "temperature": self.temperature,
            "base_branch": self.base_branch,
            "system_message": self.system_message,
            "review_instructions": self.review_instructions,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        # Handle type conversion for temperature
        if "temperature" in data:
            try:
                data["temperature"] = float(data["temperature"])
            except (ValueError, TypeError):
                data["temperature"] = DEFAULT_TEMPERATURE

        return cls(
            model=data.get("model", DEFAULT_MODEL),
            temperature=data.get("temperature", DEFAULT_TEMPERATURE),
            base_branch=data.get("base_branch", DEFAULT_BASE_BRANCH),
            system_message=data.get("system_message", DEFAULT_SYSTEM_MESSAGE),
            review_instructions=data.get("review_instructions", DEFAULT_REVIEW_INSTRUCTIONS),
        )


class GitHandler:
    def __init__(self, repo_path: str = "."):
        try:
            self.repo = git.Repo(repo_path)
        except git.InvalidGitRepositoryError as err:
            raise click.ClickException("Not a git repository") from err

    def get_current_branch(self) -> str:
        return self.repo.active_branch.name

    def get_default_base_branch(self) -> str:
        """Detect the default base branch (main or master)"""
        # First try to get the base branch from the existing branches
        for base in DEFAULT_BASE_BRANCHES:
            if base in self.repo.heads:
                try:
                    # Verify the branch exists and is valid
                    self.repo.git.rev_parse(f"{base}")
                    return base
                except git.GitCommandError:
                    continue

        # If no valid base branch is found
        raise click.ClickException(
            f"No default base branch found. Expected one of: {', '.join(DEFAULT_BASE_BRANCHES)}"
        )

    def get_branch_diff(
        self, branch_name: str, base_branch: Optional[str] = None, files: Optional[List[str]] = None
    ) -> str:
        """Get diff between specified branch and base branch, optionally filtered by files"""
        try:
            if base_branch is None:
                base_branch = self.get_default_base_branch()

            if branch_name == base_branch:
                existing_branches = [b.name for b in self.repo.heads if b.name != base_branch]
                example_branch = existing_branches[0] if existing_branches else "feature-branch"

                hint = (
                    f"\nTo review changes:\n"
                    f"• From main branch:\n"
                    f"  coderev review {example_branch}\n"
                    f"• After switching branch:\n"
                    f"  git checkout {example_branch}\n"
                    f"  coderev review"
                )

                raise click.ClickException(f"Cannot review the main branch against itself.\n{hint}")

            # Ensure both branches exist
            if branch_name not in self.repo.heads:
                raise click.ClickException(f"Branch '{branch_name}' not found")

            try:
                # Try to get the diff
                if files:
                    # Get diff for specific files
                    diff = self.repo.git.diff(f"{base_branch}...{branch_name}", "--", *files)
                else:
                    # Get diff for all files
                    diff = self.repo.git.diff(f"{base_branch}...{branch_name}")
            except git.GitCommandError as err:
                # If the first attempt fails with main, try master
                if base_branch == DEFAULT_BASE_BRANCH and "unknown revision" in str(err):
                    base_branch = "master"
                    if files:
                        diff = self.repo.git.diff(f"{base_branch}...{branch_name}", "--", *files)
                    else:
                        diff = self.repo.git.diff(f"{base_branch}...{branch_name}")
                else:
                    raise

            if not diff:
                if files:
                    raise click.ClickException(
                        f"No changes found between {branch_name} and {base_branch} "
                        f"for the specified files: {', '.join(files)}"
                    )
                else:
                    raise click.ClickException(
                        f"No changes found between {branch_name} and {base_branch}"
                    )

            return diff
        except git.GitCommandError as err:
            raise click.ClickException(
                f"Git error: Could not get diff between '{branch_name}' and '{base_branch}'. "
                f"Make sure both branches exist and have common history."
            ) from err
        except Exception as err:
            if isinstance(err, click.ClickException):
                raise err
            raise click.ClickException(f"Error getting diff: {str(err)}") from err

    def get_changed_files(self, branch_name: str, base_branch: Optional[str] = None) -> List[str]:
        """Get list of files changed between branches"""
        try:
            if base_branch is None:
                base_branch = self.get_default_base_branch()

            try:
                diff_files = self.repo.git.diff(
                    f"{base_branch}...{branch_name}", "--name-only"
                ).split("\n")
            except git.GitCommandError as err:
                # If the first attempt fails with main, try master
                if base_branch == DEFAULT_BASE_BRANCH and "unknown revision" in str(err):
                    base_branch = "master"
                    diff_files = self.repo.git.diff(
                        f"{base_branch}...{branch_name}", "--name-only"
                    ).split("\n")
                else:
                    raise
            # Filter out empty strings
            return [f for f in diff_files if f]
        except git.GitCommandError as err:
            raise click.ClickException(
                f"Git error: Could not get changed files. {str(err)}"
            ) from err

    def list_branches(self) -> List[str]:
        """List all branches in the repository"""
        return [branch.name for branch in self.repo.heads]


class CodeReviewer:
    def __init__(self, repo_path: str = ".", debug: bool = False):
        self.git = GitHandler(repo_path)
        self.console = Console()
        self.debug = debug or os.getenv("CODEREV_DEBUG_ENABLED", "false").lower() == "true"
        self.config = self._load_config()

    def _load_config(self) -> Config:
        config_path = Path(self.git.repo.working_dir) / CONFIG_FILENAME
        if not config_path.exists():
            return Config()
        try:
            with open(config_path) as f:
                data = json.load(f)
            return Config.from_dict(data)
        except Exception as err:
            self.console.print(f"[yellow]Warning: Could not load config file: {err}[/]")
            return Config()

    def _save_config(self):
        config_path = Path(self.git.repo.working_dir) / CONFIG_FILENAME
        try:
            with open(config_path, "w") as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as err:
            raise click.ClickException(f"Error saving config: {str(err)}") from err

    def _debug_print(self, title: str, content: str):
        if self.debug:
            self.console.print(
                Panel(
                    Syntax(content, "python", theme="monokai"),
                    title=f"[blue]{title}[/]",
                    border_style="blue",
                )
            )

    def _format_review_content(self, content: str) -> str:
        """Format the review content for display"""
        try:
            content = content.strip()

            # Find the outermost JSON code block
            start_pattern = r"^\s*```(?:json)?\s*\{"
            end_pattern = r"\}\s*```\s*$"

            start_match = re.search(start_pattern, content, re.MULTILINE)
            end_match = re.search(end_pattern, content, re.MULTILINE)

            if start_match and end_match:
                # Extract everything between the outermost code block markers
                json_content = content[start_match.start() : end_match.end()]
                # Remove the ```json prefix and ``` suffix
                json_content = re.sub(r"^\s*```(?:json)?\s*", "", json_content)
                json_content = re.sub(r"\s*```\s*$", "", json_content)

                try:
                    # Parse the JSON and extract the response
                    data = json.loads(json_content)
                    return data.get("response", json_content)
                except json.JSONDecodeError:
                    if self.debug:
                        self.console.print("[yellow]Warning: Failed to parse JSON content[/]")
                    return content

            return content

        except Exception as err:
            if self.debug:
                self.console.print(f"[yellow]Warning: Error formatting content: {str(err)}[/]")
            return content

    def review_branch(
        self,
        branch_name: str,
        base_branch: Optional[str] = None,
        files: Optional[List[str]] = None,
        system_message: Optional[str] = None,
        review_instructions: Optional[str] = None,
    ) -> str:
        try:
            if not base_branch:
                try:
                    base_branch = self.config.base_branch
                except AttributeError:
                    base_branch = self.git.get_default_base_branch()

            # Get changed files if files parameter is not provided
            changed_files = self.git.get_changed_files(branch_name, base_branch)

            # Add files information to the message
            files_info = ""
            if files:
                files_info = "\nReviewing specific files:\n" + "\n".join(f"- {f}" for f in files)
            else:
                files_info = "\nChanged files:\n" + "\n".join(f"- {f}" for f in changed_files)

            diff = self.git.get_branch_diff(branch_name, base_branch, files)

            # Use review instructions in the same priority as system message:
            # 1. Explicitly provided via --review-instructions
            # 2. Configured in .coderev.config
            # 3. Default review instructions
            effective_instructions = review_instructions or self.config.review_instructions

            user_msg = f"""Reviewing changes in branch '{branch_name}' compared to '{base_branch}'.
{files_info}

{effective_instructions}

Please review the following changes:

{diff}"""

            # Use system message in this priority:
            # 1. Explicitly provided via --system-message
            # 2. Configured in .coderev.config
            # 3. Default system message
            effective_system_msg = system_message or self.config.system_message

            self._debug_print("System Message", effective_system_msg)
            self._debug_print("User Message", user_msg)

            response = completion(
                model=self.config.model,
                temperature=self.config.temperature,
                messages=[
                    {"role": "system", "content": effective_system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )

            review_content = response.choices[0].message.content

            if self.debug:
                self._debug_print("Raw LLM Response", review_content)

            # Format the content for display
            formatted_content = self._format_review_content(review_content)
            formatted_content = formatted_content.strip()

            return formatted_content
        except click.ClickException as err:
            raise err
        except Exception as err:
            raise click.ClickException(f"Error during review: {str(err)}") from err

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
    """Coderev - AI-powered code review tool"""
    pass


@cli.command()
def init():
    """Initialize Coderev in the current repository"""
    try:
        reviewer = CodeReviewer()
        reviewer._save_config()
        click.echo("✨ Coderev initialized successfully!")
    except click.ClickException as err:
        click.echo(f"Error: {str(err)}", err=True)


@cli.command()
@click.argument("branch_name", required=False)
@click.option("--base-branch", help="Base branch to compare against (defaults to main/master)")
@click.option(
    "--review-files",
    "-f",
    multiple=True,
    help="Specific files to review (defaults to all changed files)",
)
@click.option("--debug", is_flag=True, help="Enable debug mode (defaults to false)")
@click.option("--model", help="Specify LLM model (defaults to gpt-4o)")
@click.option("--temperature", type=float, help="Set temperature for LLM (defaults to 0.0)")
@click.option("--system-message", help="Custom system message for the LLM")
@click.option("--review-instructions", help="Custom review guidelines")
def review(
    branch_name: Optional[str],
    base_branch: Optional[str],
    review_files: Tuple[str, ...],
    debug: bool,
    model: Optional[str],
    temperature: Optional[float],
    system_message: Optional[str],
    review_instructions: Optional[str],
):
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

        # Convert files tuple to list if provided
        files_list = list(review_files) if review_files else None

        review_content = reviewer.review_branch(
            branch_name,
            base_branch=base_branch,
            files=files_list,
            system_message=system_message,
            review_instructions=review_instructions,
        )
        click.echo("\n" + review_content)
    except click.ClickException as err:
        click.echo(f"Error: {str(err)}", err=True)


@cli.command(name="list")
def list_branches():
    """List all branches"""
    try:
        reviewer = CodeReviewer()
        reviewer.list_branches()
    except click.ClickException as err:
        click.echo(f"Error: {str(err)}", err=True)


@cli.group()
def config():
    """Manage Coderev configuration"""
    pass


@config.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value"""
    try:
        reviewer = CodeReviewer()
        if hasattr(reviewer.config, key):
            # Handle type conversion for known numeric fields
            if key == "temperature":
                try:
                    value = float(value)
                except ValueError as err:
                    click.echo("Error: temperature must be a valid number", err=True)
                    raise click.ClickException("Invalid temperature value") from err

                if not (0 <= value <= 2):
                    click.echo("Error: temperature must be between 0 and 2", err=True)
                    raise click.ClickException("Temperature out of range")

            setattr(reviewer.config, key, value)
            reviewer._save_config()
            click.echo(f"✓ Set {key}={value}")
        else:
            msg = f"Error: Unknown configuration key: {key}"
            click.echo(msg, err=True)
            raise click.ClickException(msg)
    except click.ClickException as err:
        raise err


@config.command(name="get")
@click.argument("key")
def config_get(key: str):
    """Get a configuration value"""
    try:
        reviewer = CodeReviewer()
        if hasattr(reviewer.config, key):
            value = getattr(reviewer.config, key)
            click.echo(f"{key}={value}")
        else:
            click.echo(f"Error: Unknown configuration key: {key}", err=True)
    except click.ClickException as err:
        click.echo(f"Error: {str(err)}", err=True)


@config.command(name="list")
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
    except click.ClickException as err:
        click.echo(f"Error: {str(err)}", err=True)


if __name__ == "__main__":
    cli()
