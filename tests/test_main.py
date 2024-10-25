import pytest
from click.testing import CliRunner

def test_review_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['review', '1'])
    assert result.exit_code == 0

def test_debug_mode():
    reviewer = CodeReviewer(debug=True)
    assert reviewer.debug == True