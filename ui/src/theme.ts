import { useEffect, useState } from "react";

export interface ThemeDefinition {
  id: string;
  name: string;
  tagline: string;
}

export const THEMES: ThemeDefinition[] = [
  {
    id: "studio",
    name: "Studio Dark",
    tagline: "Refined dark workspace with sidebar navigation",
  },
  {
    id: "atelier",
    name: "Atelier Light",
    tagline: "Clean light dashboard with crisp surfaces",
  },
  {
    id: "terminal",
    name: "Terminal",
    tagline: "Compact developer-tool aesthetic, monospace accents",
  },
  {
    id: "editorial",
    name: "Editorial",
    tagline: "Gallery-first portfolio style with serif display type",
  },
];

const STORAGE_KEY = "im-gen-theme";
const DEFAULT_THEME = THEMES[0].id;

export function getStoredTheme(): string {
  const stored = localStorage.getItem(STORAGE_KEY);
  return THEMES.some((theme) => theme.id === stored) ? stored! : DEFAULT_THEME;
}

export function applyTheme(themeId: string) {
  document.documentElement.dataset.theme = themeId;
}

export function useTheme(): [string, (themeId: string) => void] {
  const [theme, setThemeState] = useState(getStoredTheme);

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  return [theme, setThemeState];
}
