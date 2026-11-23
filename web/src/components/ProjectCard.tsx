import Link from "next/link";
import { PROJECT_TYPE_LABELS, type SearchProject } from "@/lib/types";
import { Badge, StatusBadge } from "./ui/Badge";
import { Icon } from "./ui/Icon";

const SHORT_TYPE: Record<string, string> = {
  semester_bachelor: "BA semester",
  semester_master: "MA semester",
  master_thesis: "Master thesis",
  other: "Other",
};

export function ProjectCard({ project, past = false }: { project: SearchProject; past?: boolean }) {
  return (
    <article className="group relative rounded-xl border border-border bg-surface p-5 shadow-soft transition-all duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:shadow-lift sm:p-6">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="font-semibold text-primary-text">
          {project.labs.map((l) => l.acronym).join(" · ")}
        </span>
        {project.period && (
          <span
            className={`inline-flex items-center gap-1.5 ${past ? "text-warning-fg" : "text-fg-subtle"}`}
          >
            <Icon name="calendar" className="size-3.5" />
            {project.period}
            {past && <span className="font-medium">· past semester</span>}
          </span>
        )}
      </div>

      <h3 className="mt-2.5 text-lg leading-snug font-semibold tracking-tight text-fg">
        <Link
          href={`/projects/${project.id}/`}
          className="after:absolute after:inset-0 after:rounded-xl focus-visible:outline-none group-focus-within:underline"
        >
          {project.title}
        </Link>
      </h3>

      {project.summary && (
        <p className="mt-2 line-clamp-2 leading-relaxed text-fg-muted">{project.summary}</p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <StatusBadge status={project.status} />
        {project.types.map((t) => (
          <Badge key={t} tone="primary" title={PROJECT_TYPE_LABELS[t]}>
            {SHORT_TYPE[t]}
          </Badge>
        ))}
        {project.domains.slice(0, 3).map((d) => (
          <Badge key={d}>{d}</Badge>
        ))}
      </div>

      {project.supervisors.length > 0 && (
        <p className="mt-4 flex items-center gap-2 border-t border-border pt-4 text-sm text-fg-subtle">
          <Icon name="user" className="size-4" />
          <span className="truncate">{project.supervisors.join(", ")}</span>
        </p>
      )}

      <Icon
        name="arrowRight"
        className="absolute top-6 right-6 hidden size-5 text-fg-subtle opacity-0 transition-all duration-200 group-hover:translate-x-0.5 group-hover:opacity-100 sm:block"
      />
    </article>
  );
}
