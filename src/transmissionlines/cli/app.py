"""Define the placeholder command-line application."""

import typer

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
	"""Provide the transmission line parameter command-line interface."""