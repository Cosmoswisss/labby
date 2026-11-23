# Labby

Unofficial search engine for student projects (semester, bachelor and master projects)
offered by EPFL labs. **Not affiliated with EPFL** — each lab's own page is the reference.

**Live site: https://labby-seven.vercel.app**

Status: **phase 4 — automation** (IC school and its accredited labs). See
[docs/data-sources.md](docs/data-sources.md) for the data-source exploration.

## How it works

```text
labs.yaml ──► crawl (cache + change detection) ──► LLM extraction ──► data/projects.json ──► website
              phase 1 ✅                            phase 2 ✅         phase 2 ✅              phase 3 ✅
```

## Pipeline (Python)

Requirements: [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 by itself) and, for
the extraction, [Claude Code](https://docs.claude.com/en/docs/claude-code) logged in with a
Claude subscription (no paid API key).

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

### 3. Extraction — `uv run pipeline extract`

Sends each crawled page's clean text to Claude Code in non-interactive mode
(`claude -p --json-schema …`, model `haiku`, no tools, our own system prompt) and stores
the projects found per page in `pipeline/state/extractions.json` (committed).

- Only **new or changed pages** are sent (content hash, prompt version and model are
  compared), so weekly runs stay small.
- `--limit N` caps the number of pages per run (subscription quota); progress is saved
  after every page, a later run resumes where the previous one stopped.
- `--dry-run` estimates the input tokens without calling anything.
- Prompt: `pipeline/src/pipeline/prompts/extract_v2.md` (versioned; editing it triggers a
  re-extraction). Schema: `ExtractedProject` / `PageExtraction` in `models.py`.
- Never extracts students' names: only supervisors/contacts.

### 4. Evaluation — `uv run pipeline eval`

27 hand-annotated pages (`pipeline/eval/gold/`) covering the difficult cases (index
pages, shared pages, archives with student names, PDFs, past-semester pages…). The command
runs the extraction on frozen page texts and reports project precision/recall and field
accuracy; each run is saved in `pipeline/eval/runs/`.

| Run | Precision | Recall | F1 | Levels | Supervisors | Status |
|---|---|---|---|---|---|---|
| haiku + extract_v1 | 0.98 | 0.97 | 0.974 | 0.97 | 1.0 | 1.0 |
| haiku + extract_v2 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.99 |

(extract_v2 was tuned on this set: expect lower scores on unseen pages.)
`--snapshot` refreshes `eval/pages/` from the crawl, `--rescore <run.json>` re-scores a
saved run without calling the LLM.

### 5. Export — `uv run pipeline export`

Writes `data/projects.json` and `data/labs.json` (merging index/sub-page duplicates and
attributing projects of shared pages) plus `pipeline/state/export_report.json`.

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

## Website (`web/`)

Next.js (App Router) + TypeScript + Tailwind CSS, exported as a **fully static site**
(`output: "export"`): no server, one HTML page per project.

```bash
cd web
npm install
npm run dev      # http://localhost:3000 (copies ../data/*.json into src/data/ first)
npm test         # vitest: search, filters, URL state, past-semester detection
npm run lint
npm run build    # static site in web/out/
```

- `/` — full-text search (MiniSearch, in the browser) + combinable filters (type,
  faculty, domain, skills, lab, status, language, past semesters), all reflected in the
  URL so a search can be shared.
- `/projects/<id>/` — project page with a link to the lab's page and the last-checked date.
- `/labs/` — every lab, with a direct link for labs without a public list.
- `/about/` — how it works, corrections and removal requests (GitHub issues).

### Deployment (Vercel)

Import the GitHub repository in Vercel with **Root Directory = `web`** (framework preset:
Next.js; keep "Include files outside the root directory" enabled, the build reads
`../data`). Every push to `main` redeploys the site.

## Automation (GitHub Actions)

- **CI** (`.github/workflows/ci.yml`), on every push and pull request: ruff + pytest for
  the pipeline, eslint + vitest + build for the website. Never calls the LLM.
- **Weekly data update** (`.github/workflows/update-data.yml`), every Monday 06:00 UTC and
  on demand (Actions → Update data → Run workflow): crawl → extract (new and changed pages
  only, `--max-input-tokens 400000` by default) → export. When data changed, it opens a
  pull request `data-update/<date>` whose description lists new, removed and updated
  projects; merging it publishes the data (Vercel redeploys `main`).
  - If the token budget or the subscription's usage limit is reached, the run stops
    cleanly and the remaining pages are extracted next week.
  - The raw download cache is kept between runs (Actions cache) for conditional requests.
  - Pull requests opened by the workflow's `GITHUB_TOKEN` do not trigger the CI workflow
    (GitHub rule); Vercel still builds a preview for them.

Setup (once):

1. `claude setup-token` (Claude Code, logged in with the Claude subscription) prints a
   long-lived token; add it as the repository secret `CLAUDE_CODE_OAUTH_TOKEN`
   (Settings → Secrets and variables → Actions).
2. Settings → Actions → General → Workflow permissions: allow GitHub Actions to create and
   approve pull requests.

To pause the weekly run: Actions → Update data → ⋯ → Disable workflow.

## License

MIT — see [LICENSE](LICENSE).
