import { useEffect, useState } from "react";
/** Returns `value`, updated only after `delayMs` has passed without it changing. */
export function useDebouncedValue(value, delayMs) {
    const [debounced, setDebounced] = useState(value);
    useEffect(() => {
        const timer = setTimeout(() => setDebounced(value), delayMs);
        return () => clearTimeout(timer);
    }, [value, delayMs]);
    return debounced;
}
