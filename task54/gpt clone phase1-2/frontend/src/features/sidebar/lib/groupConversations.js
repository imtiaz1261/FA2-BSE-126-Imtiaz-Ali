const DATE_GROUP_LABELS = {
    today: "Today",
    yesterday: "Yesterday",
    previous_7_days: "Previous 7 Days",
    older: "Older",
};
const DATE_GROUP_ORDER = ["today", "yesterday", "previous_7_days", "older"];
/**
 * Flattens conversations into a single row list — {header, header, item,
 * item, header, item, ...} — since react-window needs one flat, indexable
 * list rather than nested groups. Pinned items get their own leading
 * section regardless of date; everything else is bucketed by `date_group`
 * in the order the backend already sorted them (most recent first), so
 * this function only groups, it never re-sorts.
 */
export function buildSidebarRows(items) {
    const rows = [];
    const pinned = items.filter((c) => c.pinned);
    if (pinned.length > 0) {
        rows.push({ kind: "header", key: "group-pinned", label: "Pinned" });
        for (const c of pinned)
            rows.push({ kind: "item", key: c.id, conversation: c });
    }
    const unpinned = items.filter((c) => !c.pinned);
    for (const group of DATE_GROUP_ORDER) {
        const inGroup = unpinned.filter((c) => c.date_group === group);
        if (inGroup.length === 0)
            continue;
        rows.push({ kind: "header", key: `group-${group}`, label: DATE_GROUP_LABELS[group] });
        for (const c of inGroup)
            rows.push({ kind: "item", key: c.id, conversation: c });
    }
    return rows;
}
