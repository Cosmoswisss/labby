"use client";

import { useSyncExternalStore } from "react";

const noopSubscribe = () => () => {};

// One "now" per page load: stable across renders, null during prerendering.
let clientNow: Date | null = null;
function getNow(): Date {
  return (clientNow ??= new Date());
}

/** Current date in the browser; null while prerendering (keeps the static HTML stable). */
export function useClientNow(): Date | null {
  return useSyncExternalStore(noopSubscribe, getNow, () => null);
}

export type Theme = "light" | "dark";
const THEME_EVENT = "labby-theme-change";

function subscribeTheme(callback: () => void) {
  window.addEventListener(THEME_EVENT, callback);
  return () => window.removeEventListener(THEME_EVENT, callback);
}

function getTheme(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

/** Theme applied on <html>; null while prerendering. */
export function useTheme(): Theme | null {
  return useSyncExternalStore(subscribeTheme, getTheme, () => null);
}

export function setTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  localStorage.setItem("theme", theme);
  window.dispatchEvent(new Event(THEME_EVENT));
}
