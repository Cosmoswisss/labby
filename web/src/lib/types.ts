// Shapes of data/projects.json and data/labs.json (written by the Python pipeline).

export type ProjectType = "semester_bachelor" | "semester_master" | "master_thesis" | "other";
export type ProjectStatus = "available" | "reserved" | "unknown";
export type Language = "EN" | "FR" | "unknown";
export type LabStatus = "ok" | "none" | "restricted" | "js_rendered" | "blocked" | "error" | "auto";

export interface Project {
  id: string;
  lab_ids: string[];
  title: string;
  summary: string;
  description_url: string;
  project_types: ProjectType[];
  domains: string[];
  topics: string[];
  skills: string[];
  language: Language;
  supervisors: string[];
  status: ProjectStatus;
  academic_period: string | null;
  page_updated_at: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
  source_pages: string[];
}

export interface Lab {
  id: string;
  acronym: string;
  name: string;
  faculty: string;
  joint_faculties: string[];
  heads: string[];
  ic_domains: string[];
  research_interests: string[];
  projects_url: string | null;
  status: LabStatus;
  last_checked_at: string | null;
  project_count: number;
}

/** Light project record sent to the browser for search and filtering. */
export interface SearchProject {
  id: string;
  title: string;
  summary: string;
  labs: { id: string; acronym: string }[];
  faculties: string[];
  types: ProjectType[];
  domains: string[];
  topics: string[];
  skills: string[];
  language: Language;
  supervisors: string[];
  status: ProjectStatus;
  period: string | null;
  lastSeen: string | null;
}

export const PROJECT_TYPE_LABELS: Record<ProjectType, string> = {
  semester_bachelor: "Bachelor semester project",
  semester_master: "Master semester project",
  master_thesis: "Master thesis",
  other: "Other",
};

export const STATUS_LABELS: Record<ProjectStatus, string> = {
  available: "Available",
  reserved: "Reserved",
  unknown: "Status not stated",
};

export const LANGUAGE_LABELS: Record<Language, string> = {
  EN: "English",
  FR: "French",
  unknown: "Unknown",
};
