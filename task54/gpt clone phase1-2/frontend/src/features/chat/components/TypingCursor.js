import { jsx as _jsx } from "react/jsx-runtime";
/** Blinking cursor appended to the end of an in-progress streaming reply. */
export function TypingCursor() {
    return (_jsx("span", { "aria-hidden": "true", className: "ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-[blink_1s_step-start_infinite] bg-accent-600 dark:bg-accent-400" }));
}
