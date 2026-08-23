import React, { useState, useEffect } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@chatline/design-system/components/Button";
import { useConversationsStore } from "@/store/conversationsStore";

export function CreateFolderDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { createFolder } = useConversationsStore();

  useEffect(() => {
    if (!open) {
      setName("");
      setError(null);
    }
  }, [open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    
    if (!trimmed) {
      setError("Folder name is required");
      return;
    }

    if (trimmed.length > 100) {
      setError("Folder name must be less than 100 characters");
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      await createFolder(trimmed);
      onClose();
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create folder");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="New folder">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label htmlFor="folder-name" className="block text-body font-medium text-ink dark:text-ink-dark mb-2">
            Folder name
          </label>
          <input
            id="folder-name"
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setError(null);
            }}
            placeholder="My Project"
            maxLength={100}
            autoFocus
            disabled={isLoading}
            className="w-full px-3 py-2 rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark text-body text-ink dark:text-ink-dark placeholder:text-ink/40 dark:placeholder:text-ink-dark/40 focus:outline-none focus:ring-2 focus:ring-accent-600 dark:focus:ring-accent-400 disabled:opacity-50"
          />
          {error && (
            <p className="mt-2 text-meta text-danger">{error}</p>
          )}
        </div>

        <div className="flex gap-2 justify-end">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            loading={isLoading}
          >
            Create folder
          </Button>
        </div>
      </form>
    </Modal>
  );
}
