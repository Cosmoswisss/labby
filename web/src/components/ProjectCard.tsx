import Link from "next/link";
import { PROJECT_TYPE_LABELS, type SearchProject } from "@/lib/types";
import { Badge, StatusBadge } from "./Badges";

const SHORT_TYPE: Record<string, string> = {
  semester_bachelor: "BA semester",
  semester_master: "MA semester",
  master_thesis: "Master thesis",
  other: "Other",
};

export function ProjectCard({ project, past = false }: { project: SearchProject; past?: boolean }) {
  return (
    <article className="group relative rounded-xl border border-stone-200 bg-white p-4 shadow-sm transition hover:border-accent-300 hover:shadow dark:border-stone-800 dark:bg-stone-900 dark:hover:border-accent-700">
      <div className="mb-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-stone-500 dark:text-stone-400">
        <span className="font-semibold text-accent-700 dark:text-accent-400">
          {project.labs.map((l) => l.acronym).join(" · ")}
        </span>
        {project.period && (
          <span className={past ? "text-amber-700 dark:text-amber-400" : undefined}>
            {project.period}
            {past && " (past semester)"}
          </span>
        )}
      </div>
      <h3 className="text-base leading-snug font-semibold">
        <Link href={`/projects/${project.id}/`} className="after:absolute after:inset-0">
          {project.title}
        </Link>
      </h3>
      {project.summary && (
        <p className="mt-1 line-clamp-2 text-sm text-stone-600 dark:text-stone-300">
          {project.summary}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <StatusBadge status={project.status} />
        {project.types.map((t) => (
          <Badge key={t} title={PROJECT_TYPE_LABELS[t]}>
            {SHORT_TYPE[t]}
          </Badge>
        ))}
        {project.domains.slice(0, 3).map((d) => (
          <Badge key={d} tone="muted">
            {d}
          </Badge>
        ))}
      </div>
      {project.supervisors.length > 0 && (
        <p className="mt-2 truncate text-xs text-stone-500 dark:text-stone-400">
          {project.supervisors.join(", ")}
        </p>
      )}
    </article>
  );
}
