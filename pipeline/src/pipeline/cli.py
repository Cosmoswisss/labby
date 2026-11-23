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


@app.command()
def crawl(
    lab: list[str] = typer.Option(None, "--lab", help="Only crawl these lab ids (repeatable)."),
    offline: bool = typer.Option(False, help="Use the disk cache only, no network."),
    max_age: float = typer.Option(
        24.0, help="Reuse cached pages younger than this many hours without any request."
    ),
    max_subpages: int = typer.Option(25, help="Max sub-pages followed per lab."),
    labs_file: Path = typer.Option(config.LABS_FILE, help="Path to labs.yaml."),
) -> None:
    """Fetch every lab's project page (+ one level of sub-pages) and detect changes."""
    from datetime import timedelta

    from pipeline.crawl import Crawler
    from pipeline.fetch import Fetcher
    from pipeline.labs import load_labs

    all_labs = load_labs(labs_file)
    selected = [x for x in all_labs if not lab or x.id in lab]
    unknown = set(lab or []) - {x.id for x in all_labs}
    if unknown:
        typer.echo(f"Unknown lab id(s): {', '.join(sorted(unknown))}")
        raise typer.Exit(1)

    with Fetcher(config.CACHE_DIR, offline=offline, max_age=timedelta(hours=max_age)) as f:
        crawler = Crawler(f, config.CACHE_DIR, config.STATE_DIR, max_subpages=max_subpages)
        report = crawler.run(selected, partial=bool(lab))

    typer.echo("")
    typer.echo(f"Labs: {report.labs_total}  {report.labs_by_status}")
    typer.echo(
        f"Pages: {report.pages_total}  new={report.pages_new} changed={report.pages_changed} "
        f"unchanged={report.pages_unchanged} errors={report.pages_error}"
    )
    typer.echo(f"Fetcher: {report.fetcher}  duration={report.duration_s}s")
    for err in report.errors:
        typer.echo(f"  ! {err['lab']}: {err['status']} {err['url']} ({err['error']})")
    if report.little_text_pages:
        typer.echo(f"Pages with almost no text: {len(report.little_text_pages)}")
    typer.echo(f"State written to {config.STATE_DIR}")


if __name__ == "__main__":
    app()
