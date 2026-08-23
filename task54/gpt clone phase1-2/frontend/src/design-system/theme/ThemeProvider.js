import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
const ThemeContext = createContext(null);
function applyTheme(theme) {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.style.colorScheme = theme;
}
export function ThemeProvider({ children }) {
    const [theme, setThemeState] = useState(() => {
        const stored = window.localStorage.getItem("chatline-theme");
        return stored === "dark" ? "dark" : "light";
    });
    useEffect(() => {
        applyTheme(theme);
        window.localStorage.setItem("chatline-theme", theme);
    }, [theme]);
    const value = useMemo(() => ({
        theme,
        setTheme: setThemeState,
        toggleTheme: () => setThemeState((current) => (current === "dark" ? "light" : "dark")),
    }), [theme]);
    return _jsx(ThemeContext.Provider, { value: value, children: children });
}
export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error("useTheme must be used within ThemeProvider");
    }
    return context;
}
