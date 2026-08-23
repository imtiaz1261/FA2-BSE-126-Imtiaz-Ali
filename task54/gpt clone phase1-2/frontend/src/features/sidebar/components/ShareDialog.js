import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { conversationsApi } from "@/lib/conversationsApi";
import { useConversationsStore } from "@/store/conversationsStore";
export function ShareDialog({ conversationId, onClose, }) {
    const [shareUrl, setShareUrl] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [copied, setCopied] = useState(false);
    const items = useConversationsStore((s) => s.items);
    const setShared = useConversationsStore((s) => s.setShared);
    const open = conversationId !== null;
    const isCurrentlyShared = items.find((c) => c.id === conversationId)?.is_shared ?? false;
    useEffect(() => {
        if (!conversationId) {
            setShareUrl(null);
            return;
        }
        if (!isCurrentlyShared)
            return;
        // Re-fetch the link if this conversation was already shared before the
        // dialog opened (POST /share is idempotent — it returns the existing
        // token rather than minting a new one).
        setIsLoading(true);
        conversationsApi
            .share(conversationId)
            .then((res) => setShareUrl(res.share_url))
            .finally(() => setIsLoading(false));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [conversationId]);
    const handleCreateLink = async () => {
        if (!conversationId)
            return;
        setIsLoading(true);
        try {
            const res = await conversationsApi.share(conversationId);
            setShareUrl(res.share_url);
            setShared(conversationId, true);
        }
        finally {
            setIsLoading(false);
        }
    };
    const handleRevoke = async () => {
        if (!conversationId)
            return;
        setIsLoading(true);
        try {
            await conversationsApi.revokeShare(conversationId);
            setShareUrl(null);
            setShared(conversationId, false);
        }
        finally {
            setIsLoading(false);
        }
    };
    const handleCopy = async () => {
        if (!shareUrl)
            return;
        try {
            await navigator.clipboard.writeText(shareUrl);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        }
        catch {
            // Clipboard API can fail without permission/HTTPS — fail silently.
        }
    };
    return (_jsxs(Modal, { open: open, onClose: onClose, title: "Share conversation", children: [_jsx("p", { className: "mb-4 text-body text-ink/70 dark:text-ink-dark/70", children: "Anyone with this link can view a read-only copy of this conversation. They won't see your other conversations or be able to reply." }), shareUrl ? (_jsxs("div", { className: "flex flex-col gap-3", children: [_jsxs("div", { className: "flex gap-2", children: [_jsx(Input, { value: shareUrl, readOnly: true, className: "flex-1" }), _jsx(Button, { variant: "secondary", onClick: handleCopy, children: copied ? "Copied" : "Copy" })] }), _jsx(Button, { variant: "ghost", onClick: handleRevoke, disabled: isLoading, className: "self-start", children: "Stop sharing" })] })) : (_jsx(Button, { variant: "primary", onClick: handleCreateLink, loading: isLoading, children: "Create share link" }))] }));
}
