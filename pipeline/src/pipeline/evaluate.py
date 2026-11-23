"""Evaluation of the LLM extraction against hand-annotated pages (eval/).

- eval/eval_set.yaml       list of evaluated pages (id + URL)
- eval/pages/<id>.txt      frozen page text (gitignored, `--snapshot` creates it)
- eval/gold/<id>.yaml      expected projects, written by hand
- eval/runs/*.json         predictions + scores of each run (committed: history)

Matching: a predicted project matches an expected one when their normalised titles are
similar enough (or one contains the other). Then:
- precision / recall / F1 on projects (gold projects marked `optional` are ignored);
- field accuracy on matched projects: levels (exact set), supervisors (same last names),
  status, lab acronym. A gold field set to null is not scored.
- "unexpected names": predicted supervisors absent from the page's gold supervisors,
  listed for manual review (possible student names).
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import yaml

from pipeline.crawl import load_state
from pipeline.engines import Engine
from pipeline.extract import build_user_prompt, load_prompt
from pipeline.fetch import now_utc
from pipeline.models import Lab, PageExtraction
from pipeline.summaries import count_meta

MATCH_THRESHOLD = 0.8


def count_meta_summaries(projects: list[dict]) -> int:
    """Summaries that talk about the page or missing information (see summaries.py)."""
    return count_meta(projects)


DEFAULT_STATUS = ["available", "unknown"]


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def title_similarity(a: str, b: str) -> float:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if min(len(na), len(nb)) >= 12 and (na in nb or nb in na):
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def last_names(names: list[str]) -> set[str]:
    """'Prof. Andrea Cavallaro' / 'Cavallaro, Andrea' -> {'cavallaro'}."""
    result = set()
    for name in names:
        if "," in name:
            name = name.split(",")[0]
        tokens = [t for t in norm(name).split() if t not in {"prof", "dr", "professor"}]
        if tokens:
            result.add(tokens[-1])
    return result


def match_projects(predicted: list[dict], gold: list[dict]) -> list[tuple[int, int, float]]:
    """Greedy one-to-one matching by title similarity: [(pred_idx, gold_idx, score)]."""
    pairs = sorted(
        (
            (title_similarity(p["title"], g["title"]), i, j)
            for i, p in enumerate(predicted)
            for j, g in enumerate(gold)
        ),
        reverse=True,
    )
    used_p, used_g, matches = set(), set(), []
    for score, i, j in pairs:
        if score < MATCH_THRESHOLD:
            break
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        matches.append((i, j, score))
    return matches


@dataclass
class FieldScore:
    correct: int = 0
    total: int = 0

    def add(self, ok: bool) -> None:
        self.total += 1
        self.correct += int(ok)

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.total if self.total else None


@dataclass
class PageScore:
    page_id: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    false_positives: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)
    field_errors: list[str] = field(default_factory=list)
    unexpected_names: list[str] = field(default_factory=list)
    error: str | None = None


def score_page(page_id: str, predicted: list[dict], gold: list[dict], fields: dict) -> PageScore:
    ps = PageScore(page_id)
    matches = match_projects(predicted, gold)
    matched_p = {i for i, _, _ in matches}
    matched_g = {j for _, j, _ in matches}

    for i, p in enumerate(predicted):
        if i not in matched_p:
            ps.fp += 1
            ps.false_positives.append(p["title"])
    for j, g in enumerate(gold):
        if j not in matched_g and not g.get("optional"):
            ps.fn += 1
            ps.missed.append(g["title"])

    gold_names = last_names([n for g in gold for n in (g.get("supervisors") or [])])
    for i, j, _ in matches:
        p, g = predicted[i], gold[j]
        if g.get("optional"):
            continue
        ps.tp += 1
        if g.get("project_types") is not None:
            ok = set(p["project_types"]) == set(g["project_types"])
            fields["project_types"].add(ok)
            if not ok:
                ps.field_errors.append(
                    f"types {sorted(p['project_types'])} != {sorted(g['project_types'])}: "
                    f"{g['title']}"
                )
        if g.get("supervisors") is not None:
            ok = last_names(p["supervisors"]) == last_names(g["supervisors"])
            fields["supervisors"].add(ok)
            if not ok:
                ps.field_errors.append(
                    f"supervisors {p['supervisors']} != {g['supervisors']}: {g['title']}"
                )
        ok = p["status"] in g.get("status", DEFAULT_STATUS)
        fields["status"].add(ok)
        if not ok:
            ps.field_errors.append(f"status {p['status']}: {g['title']}")
        if g.get("lab_acronym"):
            ok = (p.get("lab_acronym") or "").upper() == g["lab_acronym"].upper()
            fields["lab_acronym"].add(ok)
            if not ok:
                ps.field_errors.append(f"lab {p.get('lab_acronym')} != {g['lab_acronym']}")

    for p in predicted:
        for name in p.get("supervisors", []):
            if not last_names([name]) & gold_names:
                ps.unexpected_names.append(name)
    return ps


def summarize(page_scores: list[PageScore], fields: dict) -> dict:
    tp = sum(p.tp for p in page_scores)
    fp = sum(p.fp for p in page_scores)
    fn = sum(p.fn for p in page_scores)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "projects": {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 3),
                     "recall": round(recall, 3), "f1": round(f1, 3)},
        "fields": {k: {"accuracy": None if v.accuracy is None else round(v.accuracy, 3),
                       "n": v.total} for k, v in fields.items()},
        "pages_with_errors": sum(1 for p in page_scores if p.error),
        "unexpected_names": sum(len(p.unexpected_names) for p in page_scores),
    }  # fmt: skip


class Evaluator:
    def __init__(self, eval_dir: Path, state_dir: Path, cache_dir: Path) -> None:
        self.eval_dir = eval_dir
        self.cache_dir = cache_dir
        self.pages = yaml.safe_load((eval_dir / "eval_set.yaml").read_text(encoding="utf-8"))[
            "pages"
        ]
        self.crawl_state = load_state(state_dir / "crawl_state.json")

    def snapshot(self) -> int:
        """Freezes the current crawled text of every evaluated page into eval/pages/."""
        out = self.eval_dir / "pages"
        out.mkdir(parents=True, exist_ok=True)
        for page in self.pages:
            info = self.crawl_state["pages"][page["url"]]
            text = (self.cache_dir / "text" / info["text_file"]).read_text(encoding="utf-8")
            (out / f"{page['id']}.txt").write_text(text, encoding="utf-8", newline="\n")
        return len(self.pages)

    def gold(self, page_id: str) -> list[dict]:
        path = self.eval_dir / "gold" / f"{page_id}.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))["projects"]

    def predict(
        self,
        engine: Engine,
        labs: list[Lab],
        prompt_name: str,
        only: set[str] | None = None,
        log=print,
    ) -> dict:
        system_prompt, prompt_id = load_prompt(prompt_name)
        schema = PageExtraction.model_json_schema()
        labs_by_id = {lab.id: lab for lab in labs}
        predictions: dict[str, dict] = {}
        for n, page in enumerate(self.pages, 1):
            if only and page["id"] not in only:
                continue
            info = self.crawl_state["pages"][page["url"]]
            text = (self.eval_dir / "pages" / f"{page['id']}.txt").read_text(encoding="utf-8")
            page_labs = [labs_by_id[i] for i in info["lab_ids"] if i in labs_by_id]
            user_prompt = build_user_prompt(
                page["url"], text, page_labs, info.get("parent_url"), date(2026, 11, 23),
                info.get("link_text"),
            )  # fmt: skip
            log(f"[{n}/{len(self.pages)}] {page['id']}")
            result = engine.run(system_prompt, user_prompt, schema)
            entry = {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens}
            try:
                if result.error:
                    raise ValueError(result.error)
                parsed = PageExtraction.model_validate(result.data)
                entry.update(page_kind=parsed.page_kind, error=None,
                             projects=[p.model_dump() for p in parsed.projects])  # fmt: skip
            except Exception as exc:
                entry.update(page_kind=None, error=str(exc)[:300], projects=[])
            predictions[page["id"]] = entry
        return {"engine": engine.name, "prompt": prompt_id, "predictions": predictions}

    def score(self, run: dict) -> tuple[dict, list[PageScore]]:
        fields = {
            k: FieldScore() for k in ("project_types", "supervisors", "status", "lab_acronym")
        }
        page_scores = []
        for page_id, pred in run["predictions"].items():
            ps = score_page(page_id, pred["projects"], self.gold(page_id), fields)
            ps.error = pred.get("error")
            page_scores.append(ps)
        summary = summarize(page_scores, fields)
        summary["meta_summaries"] = sum(
            count_meta_summaries(p["projects"]) for p in run["predictions"].values()
        )
        summary["input_tokens"] = sum(p["input_tokens"] for p in run["predictions"].values())
        summary["output_tokens"] = sum(p["output_tokens"] for p in run["predictions"].values())
        return summary, page_scores

    def save_run(self, run: dict, summary: dict, page_scores: list[PageScore]) -> Path:
        runs = self.eval_dir / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        stamp = now_utc().strftime("%Y%m%dT%H%M%S")
        name = f"{stamp}_{run['engine'].replace(':', '-')}_{run['prompt'].replace(':', '-')}.json"
        payload = {**run, "summary": summary,
                   "pages": [ps.__dict__ for ps in page_scores]}  # fmt: skip
        path = runs / name
        path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")  # fmt: skip
        return path
