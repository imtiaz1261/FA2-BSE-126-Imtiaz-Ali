import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect } from "react";
import { Input } from "@chatline/design-system/components/Input";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useConversationsStore } from "@/store/conversationsStore";
const DEBOUNCE_MS = 300;
export function SidebarSearchBox() {
    const { searchQuery, setSearchQuery, runSearch, clearSearch } = useConversationsStore();
    const debouncedQuery = useDebouncedValue(searchQuery, DEBOUNCE_MS);
    useEffect(() => {
        if (debouncedQuery.trim()) {
            void runSearch(debouncedQuery);
        }
        else {
            clearSearch();
        }
        // runSearch/clearSearch are stable Zustand actions; only the debounced
        // value should re-trigger this.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [debouncedQuery]);
    return (_jsx("div", { className: "px-2", children: _jsx(Input, { value: searchQuery, onChange: (e) => setSearchQuery(e.target.value), placeholder: "Search conversations\u2026", "aria-label": "Search conversations", leftIcon: _jsx(SearchIcon, {}), className: "h-9" }) }));
}
function SearchIcon() {
    return (_jsxs("svg", { width: "14", height: "14", viewBox: "0 0 16 16", fill: "none", "aria-hidden": "true", children: [_jsx("circle", { cx: "7", cy: "7", r: "5", stroke: "currentColor", strokeWidth: "1.3" }), _jsx("path", { d: "M11 11 14.5 14.5", stroke: "currentColor", strokeWidth: "1.3", strokeLinecap: "round" })] }));
}
