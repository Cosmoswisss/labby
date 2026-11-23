"use client";

import { setTheme, useTheme } from "@/lib/client";
import { Icon } from "./ui/Icon";

export function ThemeToggle() {
  const theme = useTheme();
  const label = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";

  return (
    <button
      type="button"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      aria-label={label}
      title={label}
      className="flex size-10 items-center justify-center rounded-[10px] text-fg-muted transition-all duration-200 hover:bg-surface-muted hover:text-fg active:scale-95"
    >
      {/* Icon rendered once the theme is known in the browser (avoids a mismatch). */}
      {theme === null ? (
        <span className="size-5" />
      ) : (
        <Icon name={theme === "dark" ? "sun" : "moon"} />
      )}
    </button>
  );
}
