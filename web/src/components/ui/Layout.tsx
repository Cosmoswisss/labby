import type { ReactNode } from "react";

export function Container({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`mx-auto w-full max-w-6xl px-5 sm:px-8 ${className}`}>{children}</div>;
}

/** Title block at the top of a page. */
export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className="pt-10 pb-8 sm:pt-14 sm:pb-10">
      {eyebrow && (
        <p className="mb-3 text-sm font-semibold tracking-wide text-primary-text">{eyebrow}</p>
      )}
      <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl lg:text-5xl">
        {title}
      </h1>
      {description && (
        <p className="mt-4 max-w-2xl text-lg leading-relaxed text-pretty text-fg-muted">
          {description}
        </p>
      )}
      {children}
    </header>
  );
}

export function Card({
  children,
  className = "",
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article" | "aside";
}) {
  return (
    <Tag className={`rounded-xl border border-border bg-surface shadow-soft ${className}`}>
      {children}
    </Tag>
  );
}
