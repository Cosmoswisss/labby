"""Pydantic schemas shared across the pipeline."""

from typing import Literal

from pydantic import BaseModel, Field

Faculty = Literal["IC", "STI", "SB", "SV", "ENAC", "CDM", "CDH", "ENT", "OTHER"]

# Hint written in labs.yaml (curated by hand):
#   auto         -> the crawler fetches the page and decides
#   none         -> no public project list (only a personal/contact page)
#   restricted   -> list behind a login / EPFL network
#   js_rendered  -> content rendered by JavaScript (e.g. Notion), not crawled in V1
#   blocked      -> the site refuses our crawler (robots.txt or 403)
SourceHint = Literal["auto", "none", "restricted", "js_rendered", "blocked"]

# What the crawler actually observed for a lab.
CrawlStatus = Literal["ok", "none", "restricted", "js_rendered", "blocked", "error"]


class Lab(BaseModel):
    """One lab (or center / teacher) as listed in labs.yaml."""

    id: str = Field(description="Stable slug, e.g. 'ic-cvlab'")
    acronym: str
    name: str
    faculty: Faculty
    joint_faculties: list[Faculty] = Field(default_factory=list)
    heads: list[str] = Field(default_factory=list, description="Public names, 'Last, First'")
    ic_domains: list[str] = Field(default_factory=list)
    research_interests: list[str] = Field(default_factory=list)
    projects_url: str | None = None
    source_type: SourceHint = "auto"
    listed_in: list[str] = Field(default_factory=list, description="Source lists, e.g. 'ic-mcs'")
    notes: str | None = None
