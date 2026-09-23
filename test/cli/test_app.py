"""Test the transmissionlines command-line application."""

from typer.testing import CliRunner

from transmissionlines.cli.app import app


def test_cli_help_renders() -> None:
    """Render help from the placeholder command-line application."""
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout