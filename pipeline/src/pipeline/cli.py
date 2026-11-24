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
    merge_epfl: bool = typer.Option(
        False,
        "--merge-epfl",
        help="Add the labs of www.epfl.ch/labs/ to the existing labs.yaml (keeps edits).",
    ),
) -> None:
    """Generate labs.yaml from the IC page, or add all EPFL labs with --merge-epfl."""
    from pipeline.fetch import Fetcher
    from pipeline.labs import (
        EPFL_LABS_URL,
        dump_labs_yaml,
        load_labs,
        merge_labs,
        parse_epfl_labs_page,
        parse_labs_page,
    )

    if merge_epfl:
        with Fetcher(config.CACHE_DIR, offline=offline) as fetcher:
            result = fetcher.fetch(EPFL_LABS_URL)
        if not result.ok:
            typer.echo(f"Could not fetch {EPFL_LABS_URL}: {result.error or result.status}")
            raise typer.Exit(1)
        incoming = parse_epfl_labs_page(result.body.decode("utf-8", errors="replace"))
        merged, added, updated = merge_labs(load_labs(output), incoming)
        dump_labs_yaml(merged, output)
        typer.echo(f"{len(incoming)} labs on {EPFL_LABS_URL}: {added} added, {updated} updated")
        typer.echo(f"  faculty: {dict(Counter(lab.faculty for lab in merged))}")
        typer.echo("New labs have no projects_url yet: run `pipeline discover`, then review.")
        return

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
def discover(
    faculty: list[str] = typer.Option(None, "--faculty", help="Only labs of these faculties."),
    lab: list[str] = typer.Option(None, "--lab", help="Only these lab ids."),
    limit: int = typer.Option(None, help="Max labs processed in this run."),
    redo: bool = typer.Option(False, "--redo", help="Also retry labs already processed."),
    labs_file: Path = typer.Option(config.LABS_FILE, help="Path to labs.yaml."),
) -> None:
    """Find the student-project page of labs that only have a homepage (writes labs.yaml)."""
    import json

    from pipeline.discover import apply_result, discover_lab
    from pipeline.fetch import Fetcher
    from pipeline.labs import dump_labs_yaml, load_labs

    all_labs = load_labs(labs_file)
    todo = [
        x
        for x in all_labs
        if not x.projects_url
        and x.homepage_url
        and x.source_type == "auto"
        and (redo or not (x.notes or "").endswith("review"))
        and (not faculty or x.faculty in {f.upper() for f in faculty})
        and (not lab or x.id in lab)
    ][:limit]
    counts: Counter[str] = Counter()
    results = []
    with Fetcher(config.CACHE_DIR) as fetcher:
        for n, x in enumerate(todo, 1):
            try:
                result = discover_lab(fetcher, x)
            except Exception as exc:  # one broken site must not stop the run
                from pipeline.discover import DiscoverResult

                result = DiscoverResult(x.id, "error", detail=f"{type(exc).__name__}: {exc}"[:200])
            apply_result(x, result)
            counts[result.status] += 1
            results.append(result.__dict__)
            typer.echo(f"[{n}/{len(todo)}] {x.id:28s} {result.status:12s} {result.url or ''}")
            if n % 20 == 0:
                dump_labs_yaml(all_labs, labs_file)  # keep progress if interrupted
    dump_labs_yaml(all_labs, labs_file)
    report = config.STATE_DIR / "discover_report.json"
    report.write_text(
        json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    typer.echo(f"\n{len(todo)} labs: {dict(counts)} (details in {report.name})")


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
        f"unchanged={report.pages_unchanged} errors={report.pages_error} "
        f"duplicates_skipped={report.pages_duplicate}"
    )
    typer.echo(f"Fetcher: {report.fetcher}  duration={report.duration_s}s")
    for err in report.errors:
        typer.echo(f"  ! {err['lab']}: {err['status']} {err['url']} ({err['error']})")
    if report.little_text_pages:
        typer.echo(f"Pages with almost no text: {len(report.little_text_pages)}")
    typer.echo(f"State written to {config.STATE_DIR}")


@app.command()
def extract(
    lab: list[str] = typer.Option(None, "--lab", help="Only pages of these lab ids."),
    limit: int = typer.Option(None, help="Max pages sent to the LLM in this run (quota)."),
    max_input_tokens: int = typer.Option(
        None, help="Stop once this many input tokens were used in this run (quota guard)."
    ),
    model: str = typer.Option("haiku", help="Claude model alias used by Claude Code."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Count pending pages, call nothing."),
    labs_file: Path = typer.Option(config.LABS_FILE, help="Path to labs.yaml."),
) -> None:
    """Extract projects from crawled pages with Claude Code (only new/changed pages)."""
    from pipeline.engines import ClaudeCodeEngine
    from pipeline.extract import Extractor
    from pipeline.labs import load_labs

    labs = load_labs(labs_file)
    extractor = Extractor(ClaudeCodeEngine(model=model), config.CACHE_DIR, config.STATE_DIR)
    from pipeline.extract import ExtractionLocked, extraction_lock

    run = lambda: extractor.run(  # noqa: E731
        labs,
        lab_ids=set(lab) if lab else None,
        limit=limit,
        max_input_tokens=max_input_tokens,
        dry_run=dry_run,
    )
    if dry_run:
        report = run()
    else:
        try:
            with extraction_lock(config.STATE_DIR):
                report = run()
        except ExtractionLocked as exc:
            typer.echo(f"Not started: {exc}")
            raise typer.Exit(2) from exc
    typer.echo("")
    typer.echo(f"Engine: {report.engine}  prompt: {report.prompt}")
    typer.echo(
        f"Pages: {report.pages_considered} considered, {report.pages_up_to_date} up to date, "
        f"{report.pages_extracted} extracted, {report.pages_failed} failed, "
        f"{report.pages_left} left"
    )
    if dry_run:
        typer.echo(f"Dry run: ~{report.input_tokens:,} input tokens would be sent.")
        return
    typer.echo(f"Projects found: {report.projects_found}")
    typer.echo(f"Tokens: {report.input_tokens:,} in / {report.output_tokens:,} out")
    if report.stopped_reason:
        typer.echo(f"Stopped early: {report.stopped_reason}")
    for err in report.errors:
        typer.echo(f"  ! {err['url']}: {err['error']}")


@app.command()
def export(
    labs_file: Path = typer.Option(config.LABS_FILE, help="Path to labs.yaml."),
) -> None:
    """Write data/projects.json and data/labs.json from the crawl + extraction state."""
    from pipeline.export import export as run_export
    from pipeline.labs import load_labs

    report = run_export(load_labs(labs_file), config.STATE_DIR, config.REPO_DIR / "data")
    typer.echo(f"Projects: {report['projects']}  {report['projects_by_status']}")
    typer.echo(f"Labs: {report['labs']} ({report['labs_with_projects']} with projects) "
               f"{report['labs_by_status']}")  # fmt: skip
    typer.echo(
        f"Pages: {report['pages_crawled']} crawled, {report['pages_extracted']} extracted, "
        f"{report['pages_failed']} failed, {report['pages_not_yet_extracted']} not yet extracted"
    )
    typer.echo(f"Extraction tokens so far: {report['extraction_tokens_in']:,} in / "
               f"{report['extraction_tokens_out']:,} out")  # fmt: skip
    typer.echo(f"Wrote {config.REPO_DIR / 'data'}")


@app.command()
def diff(
    old: Path = typer.Option(None, help="Previous data/projects.json (missing = empty)."),
    new: Path = typer.Option(config.REPO_DIR / "data" / "projects.json"),
    output: Path = typer.Option(None, help="Write the Markdown here instead of stdout."),
) -> None:
    """Markdown summary of a data update (body of the automatic pull request)."""
    from pipeline.report import render_markdown

    text = render_markdown(
        old, new, config.STATE_DIR / "crawl_report.json", config.STATE_DIR / "extract_report.json"
    )
    if output:
        output.write_text(text, encoding="utf-8", newline="\n")
    else:
        typer.echo(text)


@app.command(name="eval")
def eval_cmd(
    snapshot: bool = typer.Option(False, help="Freeze current crawled texts into eval/pages/."),
    model: str = typer.Option("haiku", help="Claude model alias used by Claude Code."),
    prompt: str = typer.Option("extract_v3", help="Prompt file name in prompts/."),
    page: list[str] = typer.Option(None, "--page", help="Only these eval page ids."),
    rescore: Path = typer.Option(None, help="Re-score a saved run file, no LLM call."),
    labs_file: Path = typer.Option(config.LABS_FILE, help="Path to labs.yaml."),
) -> None:
    """Evaluate the extraction against the hand-annotated pages in eval/."""
    import json

    from pipeline.engines import ClaudeCodeEngine
    from pipeline.evaluate import Evaluator
    from pipeline.labs import load_labs

    evaluator = Evaluator(config.PIPELINE_DIR / "eval", config.STATE_DIR, config.CACHE_DIR)
    if snapshot:
        typer.echo(f"Snapshot of {evaluator.snapshot()} pages written to eval/pages/")
        return
    if rescore:
        run = json.loads(rescore.read_text(encoding="utf-8"))
    else:
        run = evaluator.predict(
            ClaudeCodeEngine(model=model), load_labs(labs_file), prompt, set(page or [])
        )
    summary, page_scores = evaluator.score(run)
    if not rescore:
        typer.echo(f"Run saved to {evaluator.save_run(run, summary, page_scores)}")

    typer.echo("")
    for ps in page_scores:
        flag = "OK " if not (ps.fp or ps.fn or ps.field_errors or ps.error) else "-- "
        typer.echo(f"{flag}{ps.page_id:18s} tp={ps.tp:2d} fp={ps.fp:2d} fn={ps.fn:2d}")
        if ps.error:
            typer.echo(f"     error: {ps.error}")
        for t in ps.false_positives:
            typer.echo(f"     + extra:   {t}")
        for t in ps.missed:
            typer.echo(f"     - missed:  {t}")
        for e in ps.field_errors:
            typer.echo(f"     ~ {e}")
        if ps.unexpected_names:
            typer.echo(f"     ? names not in gold: {ps.unexpected_names}")
    p = summary["projects"]
    typer.echo("")
    typer.echo(f"Engine {run['engine']}  prompt {run['prompt']}")
    typer.echo(
        f"Projects: precision={p['precision']} recall={p['recall']} f1={p['f1']} "
        f"(tp={p['tp']} fp={p['fp']} fn={p['fn']})"
    )
    for name, f in summary["fields"].items():
        typer.echo(f"  {name:14s} accuracy={f['accuracy']} (n={f['n']})")
    typer.echo(f"Unexpected names: {summary['unexpected_names']}  "
               f"pages in error: {summary['pages_with_errors']}")  # fmt: skip
    typer.echo(f"Summaries mentioning the page / missing info: {summary.get('meta_summaries', 0)}")
    typer.echo(f"Tokens: {summary['input_tokens']:,} in / {summary['output_tokens']:,} out")


if __name__ == "__main__":
    app()
