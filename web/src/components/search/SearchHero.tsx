"use client";

import { Icon } from "../ui/Icon";

export function HeroShell({ children, subtitle }: { children: React.ReactNode; subtitle: string }) {
  return (
    <section aria-labelledby="hero-title" className="pt-10 pb-8 sm:pt-16 sm:pb-12">
      <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-sm font-medium text-fg-muted shadow-soft">
        <span className="size-2 rounded-full bg-success-fg" aria-hidden="true" />
        {subtitle}
      </p>
      <h1
        id="hero-title"
        className="max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-5xl lg:text-[3.5rem] lg:leading-[1.08]"
      >
        Find your next <span className="text-primary-text">semester project</span> or master
        thesis
      </h1>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-pretty text-fg-muted">
        Every open project from EPFL labs, in one place. Search by topic, skill or lab, then go
        straight to the lab&apos;s page to apply.
      </p>
      {children}
    </section>
  );
}

export function SearchBox({
  value,
  onChange,
  disabled = false,
}: {
  value: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="mt-8">
      <label htmlFor="project-search" className="sr-only">
        Search projects
      </label>
      <div className="group relative">
        <Icon
          name="search"
          className="pointer-events-none absolute top-1/2 left-5 size-5 -translate-y-1/2 text-fg-subtle transition-colors duration-200 group-focus-within:text-primary-text"
        />
        <input
          id="project-search"
          type="search"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          disabled={disabled}
          placeholder='Try "machine learning python", "robotics", "FPGA"…'
          autoComplete="off"
          className="h-14 w-full rounded-2xl border border-border bg-surface pr-12 pl-13 text-base text-fg shadow-soft transition-all duration-200 placeholder:text-fg-subtle hover:border-border-strong focus:border-primary focus:shadow-lift focus:outline-none sm:h-16 sm:text-lg [&::-webkit-search-cancel-button]:hidden"
        />
        {value && onChange && (
          <button
            type="button"
            onClick={() => onChange("")}
            aria-label="Clear search"
            className="absolute top-1/2 right-3 flex size-8 -translate-y-1/2 items-center justify-center rounded-lg text-fg-subtle transition-all duration-200 hover:bg-surface-muted hover:text-fg"
          >
            <Icon name="x" className="size-4" />
          </button>
        )}
      </div>
    </div>
  );
}

export function Suggestions({
  items,
  onPick,
}: {
  items: string[];
  onPick: (value: string) => void;
}) {
  if (!items.length) return null;
  return (
    <div className="mt-4 flex flex-wrap items-center gap-2">
      <span className="text-sm text-fg-subtle">Popular:</span>
      {items.map((item, i) => (
        <button
          key={item}
          type="button"
          onClick={() => onPick(item)}
          className={`${i >= 4 ? "hidden sm:inline-flex" : "inline-flex"} rounded-full border border-border bg-surface px-3 py-1 text-sm text-fg-muted transition-all duration-200 hover:border-primary hover:bg-primary-soft hover:text-primary-soft-fg active:scale-95`}
        >
          {item}
        </button>
      ))}
    </div>
  );
}
