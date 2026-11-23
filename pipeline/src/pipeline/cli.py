"""Command-line entry point: `uv run pipeline <command>`."""

import typer

app = typer.Typer(help="Labby data pipeline.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Labby data pipeline."""


@app.command()
def version() -> None:
    """Print the pipeline version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("labby-pipeline"))


if __name__ == "__main__":
    app()
