"""Pydantic schemas shared across the pipeline."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


# -- LLM extraction ------------------------------------------------------------------

ProjectType = Literal["semester_bachelor", "semester_master", "master_thesis", "other"]
ProjectStatus = Literal["available", "reserved", "unknown"]
Language = Literal["EN", "FR", "unknown"]
PageKind = Literal["project_list", "single_project", "no_projects", "access_restricted"]


class ExtractedProject(BaseModel):
    """One open student project, as returned by the LLM for one page."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Project title as written on the page")
    lab_acronym: str | None = Field(
        description="Acronym of the lab offering it, only when the page is shared by several "
        "labs and the page says which one; otherwise null"
    )
    summary: str = Field(description="1-3 sentence summary in English, factual, from the page")
    project_types: list[ProjectType] = Field(
        description="Levels the page says the project is open to; empty if not stated"
    )
    domains: list[str] = Field(description="2-5 short research domains, lowercase English")
    skills: list[str] = Field(description="Required or useful skills/tools named on the page")
    language: Language = Field(description="Language of the project description")
    supervisors: list[str] = Field(
        description="Supervisors/contacts named for this project. Never students."
    )
    status: ProjectStatus
    academic_period: str | None = Field(
        description="Semester the offer is for, e.g. 'Spring 2027', if stated; otherwise null"
    )


class PageExtraction(BaseModel):
    """Everything the LLM returns for one page."""

    model_config = ConfigDict(extra="forbid")

    page_kind: PageKind
    page_updated_at: str | None = Field(
        description="Last-update date shown on the page, ISO 'YYYY-MM-DD', otherwise null"
    )
    projects: list[ExtractedProject]
