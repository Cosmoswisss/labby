// Build-time data access (Server Components only): reads the pipeline output that
// scripts/copy-data.mjs copied into src/data/.

import labsJson from "@/data/labs.json";
import projectsJson from "@/data/projects.json";
import type { Lab, Project, SearchProject } from "./types";

const projects = (projectsJson as { projects: Project[] }).projects;
const labs = (labsJson as { labs: Lab[] }).labs;
const labsById = new Map(labs.map((lab) => [lab.id, lab]));

export const generatedAt: string = (projectsJson as { generated_at: string }).generated_at;

export function getProjects(): Project[] {
  return projects;
}

export function getProject(id: string): Project | undefined {
  return projects.find((p) => p.id === id);
}

export function getLabs(): Lab[] {
  return labs;
}

export function getLab(id: string): Lab | undefined {
  return labsById.get(id);
}

/** Normalised domain label: lowercase, single spaces. */
export function normalizeTag(tag: string): string {
  return tag.toLowerCase().replace(/\s+/g, " ").trim();
}

/** Light records for the browser (search, filters, result cards). */
export function getSearchProjects(): SearchProject[] {
  return projects.map((p) => {
    const projectLabs = p.lab_ids.map((id) => labsById.get(id)).filter((l): l is Lab => !!l);
    return {
      id: p.id,
      title: p.title,
      summary: p.summary,
      labs: projectLabs.map((l) => ({ id: l.id, acronym: l.acronym })),
      faculties: [...new Set(projectLabs.flatMap((l) => [l.faculty, ...l.joint_faculties]))],
      types: p.project_types,
      domains: [...new Set(p.domains.map(normalizeTag))],
      skills: [...new Set(p.skills.map((s) => s.trim()).filter(Boolean))],
      language: p.language,
      supervisors: p.supervisors,
      status: p.status,
      period: p.academic_period,
      lastSeen: p.last_seen_at,
    };
  });
}
