"""Clean the free-text domains written by the LLM and map them to a few broad topics.

No LLM involved: deterministic rules, so the website's filters stay stable from one
weekly update to the next.
- `normalize_domain`: lowercase, unified separators, common aliases ("ML", "NLP"…).
- `topics_for`: broad topics (about 15) from keyword rules on the cleaned domains.
"""

from __future__ import annotations

import re

ALIASES = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "a.i.": "artificial intelligence",
    "dl": "deep learning",
    "rl": "reinforcement learning",
    "nlp": "natural language processing",
    "llm": "large language models",
    "llms": "large language models",
    "large language model": "large language models",
    "language model": "language models",
    "cv": "computer vision",
    "hci": "human-computer interaction",
    "human computer interaction": "human-computer interaction",
    "hri": "human-robot interaction",
    "human robot interaction": "human-robot interaction",
    "gnn": "graph neural networks",
    "gnns": "graph neural networks",
    "graph neural network": "graph neural networks",
    "vlm": "vision-language models",
    "vlms": "vision-language models",
    "vision language models": "vision-language models",
    "vision-language model": "vision-language models",
    "neural networks": "deep learning",
    "deep neural networks": "deep learning",
    "iot": "internet of things",
    "internet-of-things": "internet of things",
    "fpgas": "fpga",
    "risc v": "risc-v",
    "mri": "magnetic resonance imaging",
    "eeg": "electroencephalography",
    "xai": "explainable ai",
    "explainable artificial intelligence": "explainable ai",
    "self supervised learning": "self-supervised learning",
    "3-d reconstruction": "3d reconstruction",
    "robot learning": "robot learning",
}


def normalize_domain(domain: str) -> str:
    text = domain.strip().lower()
    text = re.sub(r"\s*[-–—]\s*", "-", text)  # "human – computer" -> "human-computer"
    text = re.sub(r"\s+", " ", text).strip(" .,;")
    return ALIASES.get(text, text)


def normalize_domains(domains: list[str]) -> list[str]:
    return list(dict.fromkeys(d for d in (normalize_domain(x) for x in domains) if d))


# (topic, keywords). A domain containing a keyword gives the topic; a project can have
# several topics. Order = display order on the website.
TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "Machine learning & AI",
        (
            "machine learning",
            "deep learning",
            "reinforcement learning",
            "artificial intelligence",
            "neural network",
            "representation learning",
            "self-supervised",
            "foundation model",
            "generative",
            "diffusion model",
            "transformer",
            "federated learning",
            "explainable",
            "interpretab",
            "learning theory",
            "agentic",
            "ai ",
            "large language models",
            "multimodal learning",
            "meta-learning",
            "continual learning",
            "bayesian",
        ),
    ),
    (
        "Language & speech",
        (
            "natural language",
            "language model",
            "speech",
            "linguistic",
            "text ",
            "translation",
            "dialogue",
            "question answering",
            "information retrieval",
        ),
    ),
    (
        "Vision & imaging",
        (
            "computer vision",
            "image",
            "imaging",
            "3d reconstruction",
            "video",
            "vision-language",
            "point cloud",
            "gaussian splatting",
            "photogrammetry",
            "microscopy",
            "rendering",
            "computer graphics",
            "geometry processing",
        ),
    ),
    (
        "Robotics & control",
        (
            "robot",
            "control theory",
            "control systems",
            "motion control",
            "feedback control",
            "model predictive control",
            "optimal control",
            "drone",
            "autonomous",
            "uav",
            "locomotion",
            "manipulation",
            "navigation",
            "swarm",
            "mechatronic",
            "exoskeleton",
        ),
    ),
    (
        "Hardware & circuits",
        (
            "hardware",
            "fpga",
            "risc-v",
            "circuit",
            "asic",
            "accelerator",
            "chip",
            "embedded",
            "digital design",
            "computer architecture",
            "memory",
            "high-level synthesis",
            "vlsi",
            "processor",
            "semiconductor",
            "sensor",
            "electronics",
            "microsystem",
        ),
    ),
    (
        "Systems & networks",
        (
            "distributed",
            "operating system",
            "cloud",
            "network",
            "datacenter",
            "data center",
            "database",
            "storage",
            "wireless",
            "internet of things",
            "communication",
            "serverless",
            "computer systems",
            "operating systems",
            "scheduling",
            "edge computing",
            "blockchain",
        ),
    ),
    (
        "Security & privacy",
        (
            "security",
            "privacy",
            "cryptograph",
            "fuzzing",
            "vulnerab",
            "attack",
            "anonymi",
            "malware",
            "trust",
        ),
    ),
    (
        "Programming languages & verification",
        (
            "programming language",
            "compiler",
            "formal",
            "verification",
            "proof",
            "type system",
            "lean ",
            "software engineering",
            "static analysis",
            "program analysis",
            "rust ",
        ),
    ),
    (
        "Theory & algorithms",
        (
            "algorithm",
            "complexity",
            "combinatori",
            "graph theory",
            "information theory",
            "coding theory",
            "channel coding",
            "probability",
            "statistic",
            "optimization",
            "cryptography theory",
            "game theory",
            "learning theory",
            "inverse problem",
            "numerical",
            "approximation",
        ),
    ),
    (
        "Signal processing & acoustics",
        (
            "signal processing",
            "acoustic",
            "audio",
            "sound",
            "electroacoustic",
            "spectral",
            "sampling",
            "wavelet",
            "radar",
        ),
    ),
    (
        "Health & life sciences",
        (
            "medical",
            "biomedical",
            "health",
            "neuro",
            "biolog",
            "bioinformatic",
            "biomechanic",
            "biosensor",
            "genom",
            "protein",
            "single-cell",
            "cell biology",
            "cells ",
            "clinical",
            "brain",
            "drug",
            "molecul",
            "epidemiolog",
            "physiolog",
            "cancer",
            "chemistry",
        ),
    ),
    (
        "Humanities & society",
        (
            "digital humanities",
            "cultural heritage",
            "history",
            "histor",
            "museolog",
            "archive",
            "humanit",
            "social",
            "education",
            "epigraph",
            "newspaper",
            "music",
            "art ",
            "arts ",
            "art history",
            "democracy",
            "ethics",
            "policy",
            "law ",
            "legal",
            "journalism",
        ),
    ),
    (
        "Environment & civil engineering",
        (
            "environment",
            "climate",
            "remote sensing",
            "gis ",
            "geospatial",
            "geograph",
            "geolog",
            "geotechn",
            "geophysic",
            "urban",
            "transport",
            "energy",
            "civil",
            "hydro",
            "earth",
            "ecolog",
            "sustainab",
            "mobility",
            "building",
            "rockfall",
            "landslide",
            "natural hazard",
            "agricultur",
        ),
    ),
    (
        "Physics & materials",
        (
            "physics",
            "quantum",
            "material",
            "photonic",
            "optic",
            "mechanics",
            "granular",
            "fluid",
            "plasma",
            "thermal",
            "nano",
            "fracture",
        ),
    ),
    (
        "Human-computer interaction & design",
        (
            "human-computer interaction",
            "interaction design",
            "user ",
            "user experience",
            "user interface",
            "visualization",
            "virtual reality",
            "augmented reality",
            "ux ",
            "accessibility",
            "crowdsourc",
            "human-ai interaction",
            "tangible",
        ),
    ),
    (
        "Data science",
        (
            "data science",
            "data analysis",
            "data mining",
            "data engineering",
            "analytics",
            "big data",
            "data management",
            "time series",
        ),
    ),
    (
        "Business & entrepreneurship",
        (
            "entrepreneur",
            "innovation",
            "management",
            "economic",
            "business",
            "finance",
            "strategy",
            "market",
            "science of science",
            "industry",
        ),
    ),
]


def _compile(keywords: tuple[str, ...]) -> re.Pattern[str]:
    # Keywords match at the start of a word ("neuro" matches "neuroscience", "art " only
    # the word "art", not "artificial"); domains are padded with spaces.
    return re.compile("|".join(r"(?<![a-z0-9])" + re.escape(k) for k in keywords))


_TOPIC_PATTERNS = [(topic, _compile(keywords)) for topic, keywords in TOPIC_RULES]


def topics_for(domains: list[str]) -> list[str]:
    """Broad topics of a project from its (normalized) domains, in display order."""
    padded = [f" {d} " for d in domains]
    return [topic for topic, pattern in _TOPIC_PATTERNS if any(pattern.search(d) for d in padded)]


TOPIC_ORDER = [topic for topic, _ in TOPIC_RULES]
