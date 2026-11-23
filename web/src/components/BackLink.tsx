"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Icon } from "./ui/Icon";

/** Goes back to the previous search (keeping its filters) when coming from this site. */
export function BackLink() {
  const router = useRouter();
  return (
    <Link
      href="/"
      onClick={(e) => {
        const fromSite = document.referrer.startsWith(window.location.origin);
        if (fromSite && window.history.length > 1) {
          e.preventDefault();
          router.back();
        }
      }}
      className="group inline-flex items-center gap-1.5 rounded-lg py-1 text-sm font-medium text-fg-muted transition-colors duration-200 hover:text-fg"
    >
      <Icon
        name="arrowLeft"
        className="size-4 transition-transform duration-200 group-hover:-translate-x-0.5"
      />
      Back to search
    </Link>
  );
}
