import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Button } from "@chatline/design-system/components/Button";
import { authApi } from "@/lib/api";
/**
 * Redirects the full page (not a fetch) since the OAuth dance requires the
 * browser to actually navigate to Google/GitHub and back.
 */
function startOAuth(provider) {
    window.location.href = authApi.oauthLoginUrl(provider);
}
export function OAuthButtons() {
    return (_jsxs("div", { className: "flex flex-col gap-2", children: [_jsx(Button, { type: "button", variant: "secondary", className: "w-full", onClick: () => startOAuth("google"), leftIcon: _jsx(GoogleIcon, {}), children: "Continue with Google" }), _jsx(Button, { type: "button", variant: "secondary", className: "w-full", onClick: () => startOAuth("github"), leftIcon: _jsx(GitHubIcon, {}), children: "Continue with GitHub" }), _jsx(Button, { type: "button", variant: "secondary", className: "w-full", onClick: () => startOAuth("microsoft"), leftIcon: _jsx(MicrosoftIcon, {}), children: "Continue with Microsoft" })] }));
}
function GoogleIcon() {
    return (_jsxs("svg", { width: "16", height: "16", viewBox: "0 0 16 16", "aria-hidden": "true", children: [_jsx("path", { fill: "#4285F4", d: "M15.68 8.18c0-.57-.05-1.11-.14-1.64H8v3.1h4.3a3.68 3.68 0 0 1-1.6 2.42v2h2.58c1.51-1.39 2.4-3.44 2.4-5.88Z" }), _jsx("path", { fill: "#34A853", d: "M8 16c2.16 0 3.97-.72 5.29-1.94l-2.58-2c-.72.48-1.63.77-2.71.77-2.08 0-3.85-1.41-4.48-3.3H.85v2.07A8 8 0 0 0 8 16Z" }), _jsx("path", { fill: "#FBBC05", d: "M3.52 9.53a4.8 4.8 0 0 1 0-3.06V4.4H.85a8 8 0 0 0 0 7.2l2.67-2.07Z" }), _jsx("path", { fill: "#EA4335", d: "M8 3.17c1.18 0 2.23.4 3.06 1.2l2.29-2.29A7.9 7.9 0 0 0 8 0 8 8 0 0 0 .85 4.4l2.67 2.07C4.15 4.58 5.92 3.17 8 3.17Z" })] }));
}
function GitHubIcon() {
    return (_jsx("svg", { width: "16", height: "16", viewBox: "0 0 16 16", fill: "currentColor", "aria-hidden": "true", children: _jsx("path", { d: "M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.49c-2.22.48-2.69-1.07-2.69-1.07-.36-.93-.89-1.17-.89-1.17-.72-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.71 1.23 1.87.87 2.33.67.07-.52.28-.87.5-1.08-1.78-.2-3.64-.89-3.64-3.96 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.13 0 0 .67-.22 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.11.16 1.93.08 2.13.51.56.82 1.28.82 2.15 0 3.08-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 8 0Z" }) }));
}
function MicrosoftIcon() {
    return (_jsxs("svg", { width: "16", height: "16", viewBox: "0 0 16 16", "aria-hidden": "true", children: [_jsx("rect", { x: "0", y: "0", width: "7.2", height: "7.2", fill: "#F25022" }), _jsx("rect", { x: "8.8", y: "0", width: "7.2", height: "7.2", fill: "#7FBA00" }), _jsx("rect", { x: "0", y: "8.8", width: "7.2", height: "7.2", fill: "#00A4EF" }), _jsx("rect", { x: "8.8", y: "8.8", width: "7.2", height: "7.2", fill: "#FFB900" })] }));
}
