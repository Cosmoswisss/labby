"""Shared paths and constants for the pipeline."""

from pathlib import Path

# pipeline/ directory (this file lives in pipeline/src/pipeline/config.py)
PIPELINE_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = PIPELINE_DIR.parent

LABS_FILE = PIPELINE_DIR / "labs.yaml"
CACHE_DIR = PIPELINE_DIR / "cache"  # raw downloads + extracted text, gitignored
STATE_DIR = PIPELINE_DIR / "state"  # small committed files: hashes, crawl report

# Public page listing IC labs and accredited labs from other schools, with links to
# each lab's student-project page. Replaces the old ic-services list (404 since 2026).
IC_LABS_SOURCE_URL = (
    "https://www.epfl.ch/schools/ic/education/master/computer-science/projects-lab-mcs/"
)

USER_AGENT = (
    "LabbyBot/0.1 (unofficial EPFL student-project index; "
    "+https://github.com/Cosmoswisss/labby)"
)
