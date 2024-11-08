import pytest
from unittest.mock import Mock, patch, PropertyMock, MagicMock
import git
import json
import click
from pathlib import Path
from click.testing import CliRunner
from main import (
    GitHandler,
    CodeReviewer,
    Config,
    ReviewMode,
    cli,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE
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
    with patch('git.Repo') as mock_git_repo:
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
        "review_mode": "normal",
        "base_branch": "main"
    }

@pytest.fixture
def reviewer(git_handler, mock_config, tmp_path):
    """Create a CodeReviewer instance with mocked dependencies"""
    # Create a temporary config file
    config_path = tmp_path / ".codify.config"
    config_path.write_text(json.dumps(mock_config))
    
    with patch('pathlib.Path.exists') as mock_exists, \
         patch('pathlib.Path.__truediv__') as mock_truediv:
        
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
    assert config.review_mode == ReviewMode.NORMAL
    assert config.base_branch == "main"

def test_config_serialization():
    """Test Config serialization and deserialization"""
    config = Config(
        model="custom-model",
        temperature=0.5,
        review_mode=ReviewMode.SECURITY,
        base_branch="develop"
    )
    
    config_dict = config.to_dict()
    assert config_dict["model"] == "custom-model"
    assert config_dict["temperature"] == 0.5
    assert config_dict["review_mode"] == "security"
    assert config_dict["base_branch"] == "develop"
    
    new_config = Config.from_dict(config_dict)
    assert new_config.model == config.model
    assert new_config.temperature == config.temperature
    assert new_config.review_mode == config.review_mode
    assert new_config.base_branch == config.base_branch

def test_cli_init_command(tmp_path):
    """Test the init command"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        mock_repo = Mock(spec=git.Repo)
        type(mock_repo).working_dir = PropertyMock(return_value=str(tmp_path))
        
        with patch('git.Repo') as mock_git_repo:
            mock_git_repo.return_value = mock_repo
            result = runner.invoke(cli, ['init'])
            
            assert result.exit_code == 0
            assert "Codify initialized successfully!" in result.output
            assert (tmp_path / ".codify.config").exists()

def test_cli_review_command(reviewer, mock_repo):
    """Test the review command"""
    runner = CliRunner()
    
    # Prepare the git mock for review
    mock_repo.git.diff.return_value = "mock diff content"
    reviewer.git.get_changed_files = Mock(return_value=["file1.py"])
    
    with patch('main.CodeReviewer') as mock_reviewer_class, \
         patch('main.completion') as mock_completion:
        
        mock_reviewer_class.return_value = reviewer
        mock_completion.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock review content"))]
        )
        
        result = runner.invoke(cli, ['review', 'feature-branch'])
        assert result.exit_code == 0
        if result.exit_code != 0:
            print(f"Error output: {result.output}")  # Debug output
        assert "Mock review content" in result.output

def test_cli_list_branches(reviewer, mock_repo):
    """Test the list branches command"""
    runner = CliRunner()
    
    with patch('main.CodeReviewer') as mock_reviewer_class, \
         patch('rich.table.Table.add_row') as mock_add_row:
        
        mock_reviewer_class.return_value = reviewer
        result = runner.invoke(cli, ['list'])
        assert result.exit_code == 0

def test_config_commands(tmp_path):
    """Test configuration commands"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Setup mock repo
        mock_repo = Mock(spec=git.Repo)
        type(mock_repo).working_dir = PropertyMock(return_value=str(tmp_path))
        
        with patch('git.Repo') as mock_git_repo:
            mock_git_repo.return_value = mock_repo
            
            # Initialize config
            result = runner.invoke(cli, ['init'])
            assert result.exit_code == 0
            
            # Test setting config
            result = runner.invoke(cli, ['config', 'set', 'model', 'new-model'])
            assert result.exit_code == 0
            
            # Test getting config
            result = runner.invoke(cli, ['config', 'get', 'model'])
            assert result.exit_code == 0
            assert 'new-model' in result.output

def test_review_branch_with_files(reviewer):
    """Test reviewing specific files in a branch"""
    # Mock the git operations more thoroughly
    reviewer.git.repo.git.diff.return_value = "mock diff content"
    reviewer.git.get_changed_files = Mock(return_value=["file1.py", "file2.py"])
    reviewer.git.get_branch_diff = Mock(return_value="mock diff content")
    
    with patch('main.completion') as mock_completion:
        mock_completion.return_value = Mock(
            choices=[Mock(message=Mock(content="Mock review for specific files"))]
        )
        
        result = reviewer.review_branch(
            "feature-branch",
            base_branch="main",
            files=["test.py"]
        )
        assert "Mock review for specific files" in result

def test_model_validation(reviewer):
    """Test different model configurations and error handling"""
    import os
    from litellm import ModelResponse, Choices, Message
    
    # Save original env vars
    original_env = {
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
        'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY'),
        'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY'),
        'MISTRAL_API_KEY': os.environ.get('MISTRAL_API_KEY')
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
                Choices(
                    message=Message(
                        content="Mock review content",
                        role="assistant"
                    ),
                    index=0
                )
            ]
        )
        
        # Test missing API key error
        with pytest.raises(click.ClickException) as exc_info:
            reviewer.config.model = "gpt-4o"
            reviewer.review_branch("feature-branch")
        assert "The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable" in str(exc_info.value)
        
        # Test with valid OpenAI setup
        with patch('main.completion') as mock_completion:
            mock_completion.return_value = mock_response
            os.environ['OPENAI_API_KEY'] = 'mock-key'
            
            reviewer.config.model = "gpt-4o"
            result = reviewer.review_branch("feature-branch")
            assert "Mock review content" in result
            
            reviewer.config.model = "o1-mini"
            result = reviewer.review_branch("feature-branch")
            assert "Mock review content" in result
        
        # Test with valid Anthropic setup
        with patch('main.completion') as mock_completion:
            mock_completion.return_value = mock_response
            os.environ['ANTHROPIC_API_KEY'] = 'mock-key'
            
            reviewer.config.model = "claude-3-sonnet-20240320"
            result = reviewer.review_branch("feature-branch")
            assert "Mock review content" in result
        
        # Test with Ollama (no API key needed)
        with patch('main.completion') as mock_completion:
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
    assert "codify review" in error_message
    assert "git checkout" in error_message
    
    # Test with existing branches
    mock_branch = Mock()
    mock_branch.name = "feature-123"
    git_handler.repo.heads = [mock_branch]
    
    with pytest.raises(click.ClickException) as exc_info:
        git_handler.get_branch_diff("main", "main")
    
    error_message = str(exc_info.value)
    assert "feature-123" in error_message  # Should show real branch name in example

if __name__ == '__main__':
    pytest.main(['-v'])