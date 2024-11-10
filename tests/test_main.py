import json
from unittest.mock import Mock, PropertyMock, patch

import click
import git
import pytest
from click.testing import CliRunner
from coderev.main import (
    DEFAULT_BASE_BRANCH,
    DEFAULT_MODEL,
    DEFAULT_REVIEW_INSTRUCTIONS,
    DEFAULT_SYSTEM_MESSAGE,
    DEFAULT_TEMPERATURE,
    CodeReviewer,
    Config,
    GitHandler,
    cli,
)


@pytest.fixture
def mock_repo():
    """Create a mock git.Repo instance with required attributes"""
    mock = Mock(spec=git.Repo)

    # Mock active branch
    mock.active_branch.name = "feature-branch"

    # Mock git command interface
    mock_git = Mock()
    mock_git.diff.return_value = "mock diff content"
    type(mock).git = PropertyMock(return_value=mock_git)

    # Mock working_dir property
    type(mock).working_dir = PropertyMock(return_value="/mock/repo/path")

    # Mock heads to properly support branch existence checks
    class MockHead:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            return self.name == other

        def __str__(self):
            return self.name

    mock.heads = [MockHead("main"), MockHead("feature-branch")]

    # Mock tree for file existence checks
    mock_tree = Mock()
    mock_tree.traverse.return_value = [Mock(path="test.py"), Mock(path="file1.py")]
    mock.tree.return_value = mock_tree

    return mock


@pytest.fixture
def git_handler(mock_repo):
    """Create a GitHandler instance with mocked repo"""
    with patch("git.Repo") as mock_git_repo:
        mock_git_repo.return_value = mock_repo
        handler = GitHandler()
        handler.repo = mock_repo
        return handler


@pytest.fixture
def mock_config():
    """Create a mock config file"""
    return {
        "model": DEFAULT_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
        "base_branch": DEFAULT_BASE_BRANCH,
        "system_message": DEFAULT_SYSTEM_MESSAGE,
        "review_instructions": DEFAULT_REVIEW_INSTRUCTIONS,
    }


@pytest.fixture
def reviewer(git_handler, mock_config, tmp_path):
    """Create a CodeReviewer instance with mocked dependencies"""
    # Create a temporary config file
    config_path = tmp_path / ".coderev.config"
    config_path.write_text(json.dumps(mock_config))

    with patch("pathlib.Path.exists") as mock_exists, patch(
        "pathlib.Path.__truediv__"
    ) as mock_truediv:
        mock_exists.return_value = True
        mock_truediv.return_value = config_path

        reviewer = CodeReviewer(debug=True)
        reviewer.git = git_handler
        reviewer.config = Config.from_dict(mock_config)
        return reviewer


def test_git_handler_current_branch(git_handler):
    """Test getting current branch name"""
    assert git_handler.get_current_branch() == "feature-branch"


def test_git_handler_default_base_branch(git_handler):
    """Test getting default base branch"""
    assert git_handler.get_default_base_branch() == "main"


def test_git_handler_get_changed_files(git_handler):
    """Test getting changed files between branches"""
    git_handler.repo.git.diff.return_value = "file1.py\nfile2.py\n"
    files = git_handler.get_changed_files("feature-branch", "main")
    assert files == ["file1.py", "file2.py"]


def test_config_default_values():
    """Test Config class default values"""
    config = Config()
    assert config.model == DEFAULT_MODEL
    assert config.temperature == DEFAULT_TEMPERATURE
    assert config.base_branch == DEFAULT_BASE_BRANCH
    assert config.system_message == DEFAULT_SYSTEM_MESSAGE
    assert config.review_instructions == DEFAULT_REVIEW_INSTRUCTIONS


def test_config_serialization():
    """Test Config serialization and deserialization"""
    config = Config(
        model="custom-model",
        temperature=0.5,
        base_branch="develop",
        system_message="Custom system message",
        review_instructions="Custom review instructions",
    )

    config_dict = config.to_dict()
    assert config_dict["model"] == "custom-model"
    assert config_dict["temperature"] == 0.5
    assert config_dict["base_branch"] == "develop"
    assert config_dict["system_message"] == "Custom system message"
    assert config_dict["review_instructions"] == "Custom review instructions"

    new_config = Config.from_dict(config_dict)
    assert new_config.model == config.model
    assert new_config.temperature == config.temperature
    assert new_config.base_branch == config.base_branch
    assert new_config.system_message == config.system_message
    assert new_config.review_instructions == config.review_instructions


def test_cli_init_command(tmp_path):
    """Test the init command"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        mock_repo = Mock(spec=git.Repo)
        type(mock_repo).working_dir = PropertyMock(return_value=str(tmp_path))

        with patch("git.Repo") as mock_git_repo:
            mock_git_repo.return_value = mock_repo
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert "Coderev initialized successfully!" in result.output
            assert (tmp_path / ".coderev.config").exists()


def test_cli_review_command(reviewer, mock_repo):
    """Test the review command"""
    runner = CliRunner()

    # Prepare the git mock for review
    mock_repo.git.diff.return_value = "mock diff content"
    reviewer.git.get_changed_files = Mock(return_value=["file1.py"])

    with patch("coderev.main.CodeReviewer") as mock_reviewer_class, patch(
        "coderev.main.completion"
    ) as mock_completion:
        mock_reviewer_class.return_value = reviewer
        mock_completion.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock review content"))]
        )

        # Test basic review command
        result = runner.invoke(cli, ["review", "feature-branch"])
        assert result.exit_code == 0
        assert "Mock review content" in result.output

        # Test with all options
        result = runner.invoke(
            cli,
            [
                "review",
                "feature-branch",
                "--base-branch",
                "main",
                "--review-files",
                "test.py",
                "--system-message",
                "Custom system message",
                "--review-instructions",
                "Custom review instructions",
            ],
        )
        assert result.exit_code == 0
        assert "Mock review content" in result.output


def test_cli_list_branches(reviewer, mock_repo):
    """Test the list branches command"""
    runner = CliRunner()

    with patch("coderev.main.CodeReviewer") as mock_reviewer_class, patch(
        "rich.table.Table.add_row"
    ):
        mock_reviewer_class.return_value = reviewer
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0


def test_config_commands(tmp_path):
    """Test configuration commands"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Setup mock repo
        mock_repo = Mock(spec=git.Repo)
        type(mock_repo).working_dir = PropertyMock(return_value=str(tmp_path))

        with patch("git.Repo") as mock_git_repo:
            mock_git_repo.return_value = mock_repo

            # Initialize config
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0

            # Test setting config
            result = runner.invoke(cli, ["config", "set", "model", "new-model"])
            assert result.exit_code == 0

            # Test getting config
            result = runner.invoke(cli, ["config", "get", "model"])
            assert result.exit_code == 0
            assert "new-model" in result.output


def test_review_branch_with_files(reviewer):
    """Test reviewing specific files in a branch"""
    # Mock the git operations more thoroughly
    reviewer.git.repo.git.diff.return_value = "mock diff content"
    reviewer.git.get_changed_files = Mock(return_value=["file1.py", "file2.py"])
    reviewer.git.get_branch_diff = Mock(return_value="mock diff content")

    with patch("coderev.main.completion") as mock_completion:
        mock_completion.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock review for specific files"))]
        )

        result = reviewer.review_branch("feature-branch", base_branch="main", files=["test.py"])
        assert "Mock review for specific files" in result


def test_model_validation(reviewer):
    """Test different model configurations and error handling"""
    import os

    from litellm import Choices, Message, ModelResponse

    # Save original env vars
    original_env = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
        "MISTRAL_API_KEY": os.environ.get("MISTRAL_API_KEY"),
    }

    try:
        # Clear environment variables
        for key in original_env:
            if key in os.environ:
                del os.environ[key]

        # Mock success response
        mock_response = ModelResponse(
            id="mock-id",
            choices=[
                Choices(message=Message(content="Mock review content", role="assistant"), index=0)
            ],
        )

        # Test missing API key error
        with pytest.raises(click.ClickException) as exc_info:
            reviewer.config.model = "gpt-4o"
            reviewer.review_branch("feature-branch")
        assert (
            "The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable"
            in str(exc_info.value)
        )

        # Test with valid OpenAI setup
        with patch("coderev.main.completion") as mock_completion:
            mock_completion.return_value = mock_response
            os.environ["OPENAI_API_KEY"] = "mock-key"

            reviewer.config.model = "gpt-4o"
            result = reviewer.review_branch("feature-branch")
            assert "Mock review content" in result

            reviewer.config.model = "o1-mini"
            result = reviewer.review_branch("feature-branch")
            assert "Mock review content" in result

        # Test with valid Anthropic setup
        with patch("coderev.main.completion") as mock_completion:
            mock_completion.return_value = mock_response
            os.environ["ANTHROPIC_API_KEY"] = "mock-key"

            reviewer.config.model = "claude-3-sonnet-20240320"
            result = reviewer.review_branch("feature-branch")
            assert "Mock review content" in result

        # Test with Ollama (no API key needed)
        with patch("coderev.main.completion") as mock_completion:
            mock_completion.return_value = mock_response
            reviewer.config.model = "ollama/qwen2.5-coder"
            result = reviewer.review_branch("feature-branch")
            assert "Mock review content" in result

        # Test invalid model name
        with pytest.raises(click.ClickException) as exc_info:
            reviewer.config.model = "invalid-model"
            reviewer.review_branch("feature-branch")
        assert "Error during review" in str(exc_info.value)

    finally:
        # Restore original env vars
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]


def test_git_handler_same_branch_error(git_handler):
    """Test error message when trying to compare a branch with itself"""
    with pytest.raises(click.ClickException) as exc_info:
        git_handler.get_branch_diff("main", "main")

    error_message = str(exc_info.value)
    # Check main error message
    assert "Cannot review the main branch against itself" in error_message

    # Check help sections
    assert "To review changes:" in error_message
    assert "• From main branch:" in error_message
    assert "• After switching branch:" in error_message

    # Check commands format
    assert "coderev review" in error_message
    assert "git checkout" in error_message

    # Test with existing branches
    mock_branch = Mock()
    mock_branch.name = "feature-123"
    git_handler.repo.heads = [mock_branch]

    with pytest.raises(click.ClickException) as exc_info:
        git_handler.get_branch_diff("main", "main")

    error_message = str(exc_info.value)
    assert "feature-123" in error_message  # Should show real branch name in example


def test_git_handler_base_branch_fallback(git_handler):
    """Test fallback from main to master when main doesn't exist"""

    # Mock git command to fail for main but succeed for master
    def mock_diff(*args, **kwargs):
        if "main..." in args[0]:
            raise git.GitCommandError(
                "git",
                128,
                stderr="fatal: ambiguous argument 'coderev.main...feature-branch': unknown revision or path not in the working tree.",
            )
        elif "master..." in args[0]:
            return "file1.py\nfile2.py"
        return ""

    git_handler.repo.git.diff = Mock(side_effect=mock_diff)

    # Mock branch existence check
    class MockHead:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            return self.name == other

        def __str__(self):
            return self.name

    git_handler.repo.heads = [MockHead("master"), MockHead("feature-branch")]

    # Mock rev-parse to simulate main branch not existing but master existing
    def mock_rev_parse(ref):
        if ref == "main":
            raise git.GitCommandError("git", 128, stderr="fatal: ambiguous argument 'main'")
        return ""

    git_handler.repo.git.rev_parse = Mock(side_effect=mock_rev_parse)

    # Test get_changed_files
    files = git_handler.get_changed_files("feature-branch")
    assert files == ["file1.py", "file2.py"]

    # Test get_branch_diff
    diff = git_handler.get_branch_diff("feature-branch")
    assert diff == "file1.py\nfile2.py"


def test_git_handler_both_base_branches_missing(git_handler):
    """Test error when both main and master are missing"""

    def mock_diff(*args, **kwargs):
        raise git.GitCommandError(
            "git",
            128,
            stderr="fatal: ambiguous argument: unknown revision or path not in the working tree.",
        )

    git_handler.repo.git.diff = Mock(side_effect=mock_diff)
    git_handler.repo.heads = [Mock(name="feature-branch")]  # Only feature branch exists

    with pytest.raises(click.ClickException) as exc_info:
        git_handler.get_changed_files("feature-branch")

    assert "No default base branch found" in str(exc_info.value)


def test_system_message_cli_command(tmp_path, git_handler):
    """Test system message via CLI command"""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Setup mock repo and config
        mock_repo = Mock(spec=git.Repo)
        type(mock_repo).working_dir = PropertyMock(return_value=str(tmp_path))

        with patch("git.Repo") as mock_git_repo, patch(
            "coderev.main.completion"
        ) as mock_completion:
            mock_git_repo.return_value = mock_repo
            mock_completion.return_value = Mock(
                choices=[Mock(message=Mock(content="Mock review content"))]
            )

            # Initialize config
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0

            # Test setting system message via config
            result = runner.invoke(cli, ["config", "set", "system_message", "Custom message"])
            assert result.exit_code == 0

            # Verify system message was saved
            config_path = tmp_path / ".coderev.config"
            config_data = json.loads(config_path.read_text())
            assert config_data["system_message"] == "Custom message"

            # Test getting system message
            result = runner.invoke(cli, ["config", "get", "system_message"])
            assert result.exit_code == 0
            assert "Custom message" in result.output


def test_system_message_configuration(tmp_path, git_handler):
    """Test system message configuration and priority"""
    # Setup
    config_path = tmp_path / ".coderev.config"
    custom_config = {
        "model": "gpt-4o",
        "temperature": 0.0,
        "base_branch": "main",
        "system_message": "Custom system message from config",
    }
    config_path.write_text(json.dumps(custom_config))

    with patch("pathlib.Path.exists") as mock_exists, patch(
        "pathlib.Path.__truediv__"
    ) as mock_truediv, patch("coderev.main.completion") as mock_completion:
        mock_exists.return_value = True
        mock_truediv.return_value = config_path
        mock_completion.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock review content"))]
        )

        reviewer = CodeReviewer(debug=True)
        reviewer.git = git_handler

        # Mock git operations
        git_handler.get_changed_files = Mock(return_value=["file1.py"])
        git_handler.get_branch_diff = Mock(return_value="mock diff")

        # Test 1: Using config file system message
        reviewer.review_branch("feature-branch")
        args = mock_completion.call_args[1]
        assert args["messages"][0]["content"] == "Custom system message from config"

        # Test 2: Override with explicit system message
        explicit_msg = "Explicit system message"
        reviewer.review_branch("feature-branch", system_message=explicit_msg)
        args = mock_completion.call_args[1]
        assert args["messages"][0]["content"] == explicit_msg

        # Test 3: Fallback to default when config doesn't have system_message
        del custom_config["system_message"]
        config_path.write_text(json.dumps(custom_config))
        reviewer = CodeReviewer(debug=True)
        reviewer.git = git_handler

        reviewer.review_branch("feature-branch")
        args = mock_completion.call_args[1]
        assert args["messages"][0]["content"] == DEFAULT_SYSTEM_MESSAGE


def test_review_instructions_configuration(tmp_path, git_handler):
    """Test review instructions configuration and priority"""
    # Setup
    config_path = tmp_path / ".coderev.config"
    custom_config = {
        "model": "gpt-4o",
        "temperature": 0.0,
        "base_branch": "main",
        "system_message": DEFAULT_SYSTEM_MESSAGE,
        "review_instructions": "Custom instructions from config",
    }
    config_path.write_text(json.dumps(custom_config))

    with patch("pathlib.Path.exists") as mock_exists, patch(
        "pathlib.Path.__truediv__"
    ) as mock_truediv, patch("coderev.main.completion") as mock_completion:
        mock_exists.return_value = True
        mock_truediv.return_value = config_path
        mock_completion.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock review content"))]
        )

        reviewer = CodeReviewer(debug=True)
        reviewer.git = git_handler

        # Mock git operations
        git_handler.get_changed_files = Mock(return_value=["file1.py"])
        git_handler.get_branch_diff = Mock(return_value="mock diff")

        # Test 1: Using config file instructions
        reviewer.review_branch("feature-branch")
        args = mock_completion.call_args[1]
        assert "Custom instructions from config" in args["messages"][1]["content"]

        # Test 2: Override with explicit instructions
        explicit_instructions = "Explicit review instructions"
        reviewer.review_branch("feature-branch", review_instructions=explicit_instructions)
        args = mock_completion.call_args[1]
        assert explicit_instructions in args["messages"][1]["content"]

        # Test 3: Fallback to default when config doesn't have instructions
        del custom_config["review_instructions"]
        config_path.write_text(json.dumps(custom_config))
        reviewer = CodeReviewer(debug=True)
        reviewer.git = git_handler

        reviewer.review_branch("feature-branch")
        args = mock_completion.call_args[1]
        assert DEFAULT_REVIEW_INSTRUCTIONS in args["messages"][1]["content"]


def test_cli_review_with_instructions(reviewer, mock_repo):
    """Test review command with custom instructions"""
    runner = CliRunner()
    custom_instructions = "Focus on performance aspects"

    mock_repo.git.diff.return_value = "mock diff content"
    reviewer.git.get_changed_files = Mock(return_value=["file1.py"])

    with patch("coderev.main.CodeReviewer") as mock_reviewer_class, patch(
        "coderev.main.completion"
    ) as mock_completion:
        mock_reviewer_class.return_value = reviewer
        mock_completion.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock review content"))]
        )

        result = runner.invoke(
            cli, ["review", "feature-branch", "--review-instructions", custom_instructions]
        )
        assert result.exit_code == 0

        # Verify instructions were passed to the review method
        args = mock_completion.call_args[1]
        assert custom_instructions in args["messages"][1]["content"]


def test_cli_command_structure():
    """Test CLI command hierarchy and help messages"""
    runner = CliRunner()

    # Test main CLI help
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Coderev - AI-powered code review tool" in result.output
    assert "Commands:" in result.output
    assert "init" in result.output
    assert "review" in result.output
    assert "list" in result.output
    assert "config" in result.output

    # Test config subcommand help
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "Manage Coderev configuration" in result.output
    assert "Commands:" in result.output
    assert "set" in result.output
    assert "get" in result.output
    assert "list" in result.output


def test_temperature_configuration(tmp_path):
    """Test temperature configuration validation and type conversion"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Setup mock repo
        mock_repo = Mock(spec=git.Repo)
        type(mock_repo).working_dir = PropertyMock(return_value=str(tmp_path))

        with patch("git.Repo") as mock_git_repo:
            mock_git_repo.return_value = mock_repo

            # Initialize config
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0

            # Test valid temperatures
            valid_temps = ["0.0", "0.8", "1.0", "1.5", "2.0"]
            for temp in valid_temps:
                result = runner.invoke(cli, ["config", "set", "temperature", temp])
                assert result.exit_code == 0
                assert f"Set temperature={temp}" in result.output

                # Verify temperature is stored as float
                config_path = tmp_path / ".coderev.config"
                config_data = json.loads(config_path.read_text())
                assert isinstance(config_data["temperature"], float)
                assert config_data["temperature"] == float(temp)

            # Test invalid temperature values
            invalid_cases = [
                ("invalid", "must be a valid number"),
                ("2.1", "must be between 0 and 2"),
                # Use -- to prevent negative numbers being interpreted as options
                ("--", "-0.1", "must be between 0 and 2"),
            ]

            for case in invalid_cases:
                if len(case) == 3:
                    separator, temp, error_msg = case
                    args = ["config", "set", "temperature", separator, temp]
                else:
                    temp, error_msg = case
                    args = ["config", "set", "temperature", temp]

                result = runner.invoke(cli, args)
                assert result.exit_code != 0
                assert error_msg in result.output


def test_review_with_temperature(reviewer, mock_repo):
    """Test review command with different temperature settings"""
    runner = CliRunner()

    mock_repo.git.diff.return_value = "mock diff content"
    reviewer.git.get_changed_files = Mock(return_value=["file1.py"])

    with patch("coderev.main.CodeReviewer") as mock_reviewer_class, patch(
        "coderev.main.completion"
    ) as mock_completion:
        mock_reviewer_class.return_value = reviewer
        mock_completion.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock review content"))]
        )

        # Test with temperature via command line
        result = runner.invoke(cli, ["review", "feature-branch", "--temperature", "1.5"])
        assert result.exit_code == 0
        assert mock_completion.call_args[1]["temperature"] == 1.5

        # Test with temperature via config
        reviewer.config.temperature = 0.8
        result = runner.invoke(cli, ["review", "feature-branch"])
        assert result.exit_code == 0
        assert mock_completion.call_args[1]["temperature"] == 0.8


if __name__ == "__main__":
    pytest.main(["-v"])
