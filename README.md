# Labby

Unofficial search engine for student projects (semester, bachelor and master projects)
offered by EPFL labs. **Not affiliated with EPFL** — each lab's own page is the reference.

Status: **phase 1 — crawler** (IC school and its accredited labs). See
[docs/data-sources.md](docs/data-sources.md) for the data-source exploration.

## How it works

```text
labs.yaml ──► crawl (cache + change detection) ──► LLM extraction ──► data/projects.json ──► website
              phase 1 ✅                            phase 2            phase 2                 phase 3
```

## Pipeline (Python)

Requirements: [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 by itself).

```bash
cd pipeline
uv sync                     # install dependencies
uv run pipeline --help      # list commands
```

### 1. Lab list — `uv run pipeline labs`

Builds `pipeline/labs.yaml` from the public IC page
[“Projects in labs”](https://www.epfl.ch/schools/ic/education/master/computer-science/projects-lab-mcs/).
The file is then **reviewed by hand**; the command refuses to overwrite it unless
`--force` is given.

`source_type` per lab: `auto` (crawled), `none` (no public list), `restricted`
(login / EPFL network: only the link is shown), `js_rendered` (Notion…, not crawled
in V1), `blocked` (the site refuses crawlers).

### 2. Crawl — `uv run pipeline crawl`

For every `auto` lab: fetches the projects page, follows **one level** of in-scope
links that look like project pages or PDFs (never "completed / past / archive"
pages), extracts the main text and hashes it.

| Option | Effect |
|---|---|
| `--lab ic-cvlab` | only this lab (repeatable); other labs' state is kept |
| `--offline` | disk cache only, no network (development) |
| `--max-age 24` | reuse cached pages younger than N hours without any request |
| `--max-subpages 25` | cap on sub-pages followed per lab |

Outputs:

- `pipeline/cache/` (gitignored): raw downloads and the clean text of each page
  (`cache/text/*.txt`, input of the LLM extraction).
- `pipeline/state/crawl_state.json` (committed): status of each lab, and per page its
  labs, content hash, `first_seen_at`, `last_checked_at`, `last_changed_at`.
- `pipeline/state/crawl_report.json` (committed): summary of the last run.

### Crawling rules

- robots.txt is honoured for every host (RFC 9309: unreachable robots.txt = disallow).
- At most ~1 request/second per host, explicit User-Agent
  (`LabbyBot/0.1 (...; +https://github.com/Cosmoswisss/labby)`).
- Everything is cached; stale copies are revalidated with ETag / Last-Modified.
- Public content only: pages behind a login are marked `restricted`, never accessed
  with credentials.
- Students' names are never stored; completed/archived project pages are not followed.

### Development

```bash
cd pipeline
uv run pytest            # tests (no network: HTTP is mocked)
uv run ruff check .      # lint
uv run ruff format .     # format
```

Behind an antivirus or proxy that inspects HTTPS, `uv` may fail with
`invalid peer certificate: UnknownIssuer` when downloading packages: add
`--system-certs` (e.g. `uv sync --system-certs`). The crawler itself already uses the
operating system's certificate store (via `truststore`).

## License

MIT — see [LICENSE](LICENSE).
