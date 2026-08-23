import React from "react";
import { Button } from "@chatline/design-system/components/Button";
import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <Button variant="ghost" size="sm" onClick={toggleTheme} aria-label="Toggle theme">
      {theme === "dark" ? "Light" : "Dark"}
    </Button>
  );
}