"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ThemeToggle } from "./ThemeToggle";
import { Icon } from "./ui/Icon";

const NAV = [
  { href: "/", label: "Search" },
  { href: "/labs/", label: "Labs" },
  { href: "/about/", label: "About" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/" || pathname.startsWith("/projects");
  return pathname.startsWith(href.replace(/\/$/, ""));
}

export function Logo() {
  return (
    <Link href="/" className="group flex items-center gap-2.5" aria-label="Labby, home">
      <span className="flex size-8 items-center justify-center rounded-[9px] bg-primary text-primary-fg shadow-soft transition-transform duration-200 group-hover:-rotate-6">
        <Icon name="beaker" className="size-[18px]" strokeWidth={2} />
      </span>
      <span className="text-lg font-semibold tracking-tight">Labby</span>
    </Link>
  );
}

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Close the mobile menu after navigating, and with the Escape key.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const linkClass = (active: boolean) =>
    `rounded-[10px] px-3.5 py-2 text-sm font-medium transition-all duration-200 ${
      active
        ? "bg-primary-soft text-primary-soft-fg"
        : "text-fg-muted hover:bg-surface-muted hover:text-fg"
    }`;

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/80 backdrop-blur-lg">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-4 px-5 sm:px-8">
        <Logo />

        <nav aria-label="Main" className="ml-auto hidden items-center gap-1 sm:flex">
          {NAV.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={linkClass(active)}
              >
                {item.label}
              </Link>
            );
          })}
          <span className="mx-1.5 h-5 w-px bg-border" aria-hidden="true" />
          <ThemeToggle />
        </nav>

        <div className="ml-auto flex items-center gap-1 sm:hidden">
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            className="flex size-10 items-center justify-center rounded-[10px] text-fg-muted transition-all duration-200 hover:bg-surface-muted hover:text-fg"
          >
            <Icon name={open ? "x" : "menu"} />
          </button>
        </div>
      </div>

      {open && (
        <nav
          id="mobile-menu"
          aria-label="Main"
          className="animate-fade-in border-t border-border bg-surface px-5 pt-3 pb-5 sm:hidden"
        >
          <ul className="space-y-1">
            {NAV.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={`block ${linkClass(active)} py-3 text-base`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      )}
    </header>
  );
}
