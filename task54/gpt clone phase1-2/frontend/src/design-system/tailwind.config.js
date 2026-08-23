const config = {
    content: [],
    theme: {
        extend: {
            colors: {
                accent: {
                    600: "#2563eb",
                    700: "#1d4ed8",
                },
                border: "#e5e7eb",
                "border-dark": "#374151",
                canvas: "#ffffff",
                "canvas-dark-panel": "#111827",
                ink: "#111827",
                "ink-dark": "#f9fafb",
                danger: "#ef4444",
            },
            borderRadius: {
                control: "0.375rem",
            },
            fontSize: {
                meta: ["0.875rem", { lineHeight: "1.25rem" }],
                body: ["1rem", { lineHeight: "1.5rem" }],
            },
        },
    },
    plugins: [],
};
export default config;
