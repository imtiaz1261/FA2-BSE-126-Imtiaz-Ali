import { jsx as _jsx } from "react/jsx-runtime";
import { Button } from "@chatline/design-system/components/Button";
import { useTheme } from "./ThemeProvider";
export function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();
    return (_jsx(Button, { variant: "ghost", size: "sm", onClick: toggleTheme, "aria-label": "Toggle theme", children: theme === "dark" ? "Light" : "Dark" }));
}
