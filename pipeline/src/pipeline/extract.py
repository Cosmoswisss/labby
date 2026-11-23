"""LLM extraction: turn each crawled page's clean text into structured projects.

Incremental: a page is sent to the LLM only when its text (content hash), the prompt or
the model changed since its last extraction. Results are stored per page in
state/extractions.json (committed), so a run can stop at any time (e.g. when the Claude
quota is reached) and resume later.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from pipeline.crawl import load_state, save_json
from pipeline.engines import Engine, EngineResult
from pipeline.fetch import now_utc
from pipeline.models import Lab, PageExtraction

PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPT_NAME = "extract_v2"
MAX_PAGE_CHARS = 120_000  # ~30k tokens; longer pages are truncated (and flagged)
EXTRACTIONS_VERSION = 1
USAGE_LIMIT_RE = re.compile(r"usage limit|rate limit|limit reached|429|overloaded", re.I)


def load_prompt(name: str = PROMPT_NAME) -> tuple[str, str]:
    """Returns (prompt text, short hash). The hash changes whenever the prompt is edited."""
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    return text, f"{name}:{hashlib.sha256(text.encode()).hexdigest()[:8]}"


def build_user_prompt(
    page_url: str,
    text: str,
    labs: list[Lab],
    parent_url: str | None,
    today: date,
    link_text: str | None = None,
) -> str:
    lab_lines = "\n".join(f"- {lab.acronym}: {lab.name}" for lab in labs)
    shared = "yes" if len(labs) > 1 else "no"
    position = f"sub-page linked from {parent_url}" if parent_url else "main projects page"
    if parent_url and link_text:
        position += f'\nText of the link to this page on the parent page: "{link_text}"'
    truncated = ""
    if len(text) > MAX_PAGE_CHARS:
        text = text[:MAX_PAGE_CHARS]
        truncated = "\n[... page truncated ...]"
    return (
        f"Today's date: {today.isoformat()}\n"
        f"Page URL: {page_url}\n"
        f"Page position: {position}\n"
        f"Page shared by several labs: {shared}\n"
        f"Lab(s):\n{lab_lines}\n\n"
        f"<page_text>\n{text}{truncated}\n</page_text>"
    )


@dataclass
class ExtractReport:
    started_at: str
    engine: str
    prompt: str
    finished_at: str = ""
    duration_s: float = 0.0
    pages_considered: int = 0
    pages_up_to_date: int = 0
    pages_extracted: int = 0
    pages_failed: int = 0
    pages_left: int = 0  # still to do because of --limit / budget / usage limit
    stopped_reason: str | None = None
    projects_found: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    errors: list[dict] = field(default_factory=list)


class Extractor:
    def __init__(
        self,
        engine: Engine,
        cache_dir: Path,
        state_dir: Path,
        *,
        prompt_name: str = PROMPT_NAME,
        max_attempts: int = 2,
        today: date | None = None,
        log=print,
    ) -> None:
        self.engine = engine
        self.text_dir = cache_dir / "text"
        self.state_dir = state_dir
        self.system_prompt, self.prompt_id = load_prompt(prompt_name)
        self.schema = PageExtraction.model_json_schema()
        self.max_attempts = max_attempts
        self.today = today or date.today()
        self.log = log
        self.crawl_state = load_state(state_dir / "crawl_state.json")
        self.store = load_extractions(state_dir / "extractions.json")

    def _key(self, page: dict) -> dict:
        return {
            "content_hash": page["content_hash"],
            "prompt": self.prompt_id,
            "engine": self.engine.name,
        }

    def pending_pages(self, lab_ids: set[str] | None = None) -> list[str]:
        """Pages whose stored extraction is missing or stale, in a stable order."""
        pending = []
        for url, page in self.crawl_state["pages"].items():
            if lab_ids and not set(page["lab_ids"]) & lab_ids:
                continue
            stored = self.store["pages"].get(url)
            if stored and stored.get("key") == self._key(page) and not stored.get("error"):
                continue
            pending.append(url)
        return pending

    def run(
        self,
        labs: list[Lab],
        *,
        lab_ids: set[str] | None = None,
        limit: int | None = None,
        max_input_tokens: int | None = None,
        dry_run: bool = False,
    ) -> ExtractReport:
        t0 = time.monotonic()
        report = ExtractReport(
            started_at=now_utc().isoformat(timespec="seconds"),
            engine=self.engine.name,
            prompt=self.prompt_id,
        )
        labs_by_id = {lab.id: lab for lab in labs}
        considered = [
            u
            for u, p in self.crawl_state["pages"].items()
            if not lab_ids or set(p["lab_ids"]) & lab_ids
        ]
        pending = self.pending_pages(lab_ids)
        report.pages_considered = len(considered)
        report.pages_up_to_date = len(considered) - len(pending)
        todo = pending[:limit] if limit is not None else pending
        report.pages_left = len(pending) - len(todo)
        if not dry_run and not lab_ids:
            # Forget pages the crawler no longer visits (removed links, scope changes).
            for url in set(self.store["pages"]) - set(self.crawl_state["pages"]):
                del self.store["pages"][url]
            self._save()

        if dry_run:
            chars = sum(self.crawl_state["pages"][u]["text_chars"] for u in todo)
            # ~4 chars/token + system prompt and schema overhead per call, x1.75: measured on
            # the eval set (Claude Code's structured output takes an extra turn).
            report.input_tokens = int((chars // 4 + len(todo) * 2_000) * 1.75)
            report.pages_left = len(pending)
            return report

        for n, url in enumerate(todo, 1):
            if max_input_tokens is not None and report.input_tokens >= max_input_tokens:
                report.stopped_reason = f"token budget reached ({max_input_tokens:,})"
                report.pages_left += len(todo) - n + 1
                break
            page = self.crawl_state["pages"][url]
            page_labs = [labs_by_id[i] for i in page["lab_ids"] if i in labs_by_id]
            self.log(f"[{n}/{len(todo)}] {url}")
            entry = self._extract_page(url, page, page_labs, report)
            self.store["pages"][url] = entry
            # Save after every page: a run interrupted by the quota keeps its progress.
            self._save()
            if entry["error"] and USAGE_LIMIT_RE.search(entry["error"]):
                # Subscription limit hit: stop instead of failing every remaining page.
                report.stopped_reason = f"usage limit: {entry['error'][:120]}"
                report.pages_left += len(todo) - n
                break

        report.finished_at = now_utc().isoformat(timespec="seconds")
        report.duration_s = round(time.monotonic() - t0, 1)
        save_json(self.state_dir / "extract_report.json", report.__dict__)
        return report

    def _extract_page(self, url: str, page: dict, labs: list[Lab], report) -> dict:
        text = (self.text_dir / page["text_file"]).read_text(encoding="utf-8")
        user_prompt = build_user_prompt(
            url, text, labs, page.get("parent_url"), self.today, page.get("link_text")
        )
        entry = {
            "key": self._key(page),
            "lab_ids": page["lab_ids"],
            "extracted_at": now_utc().isoformat(timespec="seconds"),
            "input_tokens": 0,
            "output_tokens": 0,
            "truncated": len(text) > MAX_PAGE_CHARS,
            "error": None,
            "page_kind": None,
            "page_updated_at": None,
            "projects": [],
        }
        error = "no attempt"
        for _attempt in range(self.max_attempts):
            result: EngineResult = self.engine.run(self.system_prompt, user_prompt, self.schema)
            entry["input_tokens"] += result.input_tokens
            entry["output_tokens"] += result.output_tokens
            report.input_tokens += result.input_tokens
            report.output_tokens += result.output_tokens
            if result.error:
                error = result.error
                continue
            try:
                parsed = PageExtraction.model_validate(result.data)
            except ValidationError as exc:
                error = f"invalid output: {exc.errors()[:2]}"[:300]
                continue
            entry.update(
                page_kind=parsed.page_kind,
                page_updated_at=parsed.page_updated_at,
                projects=[p.model_dump() for p in parsed.projects if p.title.strip()],
            )
            report.pages_extracted += 1
            report.projects_found += len(entry["projects"])
            return entry

        report.pages_failed += 1
        report.errors.append({"url": url, "error": error})
        self.log(f"   ! {error}")
        previous = self.store["pages"].get(url)
        if previous and not previous.get("error"):
            # Keep the last good extraction (its key still has the old content hash, so the
            # page stays pending and is retried next run) instead of losing its projects.
            return {**previous, "last_error": error, "last_error_at": entry["extracted_at"]}
        entry["error"] = error
        return entry

    def _save(self) -> None:
        self.store["updated_at"] = now_utc().isoformat(timespec="seconds")
        self.store["pages"] = dict(sorted(self.store["pages"].items()))
        save_json(self.state_dir / "extractions.json", self.store)


def load_extractions(path: Path) -> dict:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") == EXTRACTIONS_VERSION:
            return data
    return {"version": EXTRACTIONS_VERSION, "updated_at": None, "pages": {}}
