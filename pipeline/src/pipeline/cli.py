"""Command-line entry point: `uv run pipeline <command>`."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import typer

from pipeline import config

app = typer.Typer(help="Labby data pipeline.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Labby data pipeline."""


@app.command()
def version() -> None:
    """Print the pipeline version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("labby-pipeline"))


@app.command()
def labs(
    output: Path = typer.Option(config.LABS_FILE, help="Where to write labs.yaml."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing labs.yaml."),
    offline: bool = typer.Option(False, help="Use the cached source page only."),
) -> None:
    """Generate labs.yaml from the public IC 'projects in labs' page."""
    from pipeline.fetch import Fetcher
    from pipeline.labs import dump_labs_yaml, parse_labs_page

    if output.exists() and not force:
        typer.echo(f"{output} already exists (it may contain manual edits). Use --force.")
        raise typer.Exit(1)

    with Fetcher(config.CACHE_DIR, offline=offline) as fetcher:
        result = fetcher.fetch(config.IC_LABS_SOURCE_URL)
    if not result.ok:
        typer.echo(f"Could not fetch {config.IC_LABS_SOURCE_URL}: {result.error or result.status}")
        raise typer.Exit(1)

    parsed = parse_labs_page(result.body.decode("utf-8", errors="replace"))
    dump_labs_yaml(parsed, output)
    by_type = Counter(lab.source_type for lab in parsed)
    by_faculty = Counter(lab.faculty for lab in parsed)
    typer.echo(f"Wrote {len(parsed)} labs to {output}")
    typer.echo(f"  source_type: {dict(by_type)}")
    typer.echo(f"  faculty:     {dict(by_faculty)}")


if __name__ == "__main__":
    app()
