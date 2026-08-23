import React, { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { MemoryItemCard, MemorySettingsPanel } from "@/components/memory";

export interface MemoryItem {
  id: string;
  fact: string;
  category: string;
  relevance_score: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  source_conversation_id?: string;
}

export interface MemorySettings {
  memory_enabled: boolean;
  auto_extract_enabled: boolean;
  max_memory_items: number;
  context_injection_count: number;
  retrieval_threshold: number;
  retention_days: number;
}

interface MemoryStats {
  total_memories: number;
  by_category: Record<string, number>;
  latest_extraction?: {
    created_at: string;
    facts_extracted: number;
    facts_rejected: number;
  };
}

const CATEGORIES = [
  { value: "personal_info", label: "👤 Personal Info" },
  { value: "preferences", label: "⚙️ Preferences" },
  { value: "goals_and_values", label: "🎯 Goals & Values" },
  { value: "skills_and_expertise", label: "💡 Skills" },
  { value: "constraints", label: "⏱️ Constraints" },
  { value: "recurring_tasks", label: "🔄 Recurring Tasks" },
  { value: "project_context", label: "📁 Projects" },
  { value: "other", label: "📝 Other" },
];

export const ManageMemory: React.FC = () => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [settings, setSettings] = useState<MemorySettings | null>(null);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [newFact, setNewFact] = useState("");
  const [newCategory, setNewCategory] = useState("other");
  const [isExtracting, setIsExtracting] = useState(false);

  // Fetch memories, settings, and stats
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [memoriesRes, settingsRes, statsRes] = await Promise.all([
          fetch("/api/memory/items?limit=100"),
          fetch("/api/memory/settings"),
          fetch("/api/memory/stats"),
        ]);

        if (memoriesRes.ok) {
          const data = await memoriesRes.json();
          setMemories(data.items || []);
        }

        if (settingsRes.ok) {
          setSettings(await settingsRes.json());
        }

        if (statsRes.ok) {
          setStats(await statsRes.json());
        }
      } catch (error) {
        console.error("Failed to fetch memory data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleUpdateSettings = async (newSettings: Partial<MemorySettings>) => {
    try {
      const params = new URLSearchParams();
      Object.entries(newSettings).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, String(value));
        }
      });

      const response = await fetch(`/api/memory/settings?${params}`, {
        method: "PUT",
      });

      if (response.ok) {
        setSettings((prev) => ({ ...prev!, ...newSettings }));
      }
    } catch (error) {
      console.error("Failed to update settings:", error);
    }
  };

  const handleAddMemory = async () => {
    if (!newFact.trim()) return;

    try {
      const params = new URLSearchParams({
        fact: newFact,
        category: newCategory,
      });

      const response = await fetch(`/api/memory/items?${params}`, {
        method: "POST",
      });

      if (response.ok) {
        const item = await response.json();
        setMemories((prev) => [item, ...prev]);
        setNewFact("");
        setNewCategory("other");
      }
    } catch (error) {
      console.error("Failed to add memory:", error);
    }
  };

  const handleUpdateMemory = async (id: string, fact: string) => {
    try {
      const params = new URLSearchParams({ fact });

      const response = await fetch(`/api/memory/items/${id}?${params}`, {
        method: "PUT",
      });

      if (response.ok) {
        setMemories((prev) =>
          prev.map((m) => (m.id === id ? { ...m, fact } : m))
        );
      }
    } catch (error) {
      console.error("Failed to update memory:", error);
    }
  };

  const handleToggleActive = async (id: string, isActive: boolean) => {
    try {
      const params = new URLSearchParams({ is_active: String(isActive) });

      const response = await fetch(`/api/memory/items/${id}?${params}`, {
        method: "PUT",
      });

      if (response.ok) {
        setMemories((prev) =>
          prev.map((m) => (m.id === id ? { ...m, is_active: isActive } : m))
        );
      }
    } catch (error) {
      console.error("Failed to toggle memory active state:", error);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      const response = await fetch(`/api/memory/items/${id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        setMemories((prev) => prev.filter((m) => m.id !== id));
      }
    } catch (error) {
      console.error("Failed to delete memory:", error);
    }
  };

  const handleTriggerExtraction = async () => {
    setIsExtracting(true);
    try {
      const response = await fetch("/api/memory/extract", { method: "POST" });

      if (response.ok) {
        const result = await response.json();
        // Refresh memories after extraction
        const memoriesRes = await fetch("/api/memory/items?limit=100");
        if (memoriesRes.ok) {
          const data = await memoriesRes.json();
          setMemories(data.items || []);
        }
      }
    } catch (error) {
      console.error("Failed to trigger extraction:", error);
    } finally {
      setIsExtracting(false);
    }
  };

  const filteredMemories =
    selectedCategory && selectedCategory !== "all"
      ? memories.filter((m) => m.category === selectedCategory)
      : memories;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin w-8 h-8 border-4 border-accent-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-heading-lg font-bold text-ink dark:text-ink-dark">
          Manage Memory
        </h1>
        <p className="text-body text-ink-secondary dark:text-ink-secondary-dark">
          View and manage your saved preferences, skills, and personal facts
        </p>
      </div>

      {/* Memory Settings Panel */}
      {settings && (
        <MemorySettingsPanel settings={settings} onUpdate={handleUpdateSettings} />
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <Card className="p-4">
            <div className="text-3xl font-bold text-accent-600">
              {stats.total_memories}
            </div>
            <div className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-1">
              Total Facts
            </div>
          </Card>

          <Card className="p-4">
            <div className="text-3xl font-bold text-accent-600">
              {Object.keys(stats.by_category).length}
            </div>
            <div className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-1">
              Categories
            </div>
          </Card>

          <Card className="p-4">
            <Button
              onClick={handleTriggerExtraction}
              loading={isExtracting}
              size="sm"
              className="w-full"
            >
              🔄 Extract Now
            </Button>
            <div className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-2 text-center">
              Manual extraction
            </div>
          </Card>
        </div>
      )}

      {/* Add new memory */}
      {settings?.memory_enabled && (
        <Card className="space-y-4">
          <h3 className="text-heading-sm font-semibold text-ink dark:text-ink-dark">
            Add New Memory
          </h3>

          <textarea
            value={newFact}
            onChange={(e) => setNewFact(e.target.value)}
            placeholder="Enter a fact about yourself..."
            className="w-full px-3 py-2 rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark text-ink dark:text-ink-dark placeholder-ink-secondary dark:placeholder-ink-secondary-dark focus:outline-none focus:border-accent-600 font-sans text-body"
            rows={3}
          />

          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <label className="block text-meta text-ink-secondary dark:text-ink-secondary-dark mb-1">
                Category
              </label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark text-ink dark:text-ink-dark"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            <Button
              onClick={handleAddMemory}
              disabled={!newFact.trim()}
              size="sm"
            >
              Add Memory
            </Button>
          </div>
        </Card>
      )}

      {/* Category filter */}
      {settings?.memory_enabled && (
        <div className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setSelectedCategory(null)}
              className={cn(
                "px-3 py-1 rounded-control text-meta transition-colors",
                !selectedCategory
                  ? "bg-accent-600 text-white"
                  : "bg-canvas-panel dark:bg-canvas-dark-panel text-ink dark:text-ink-dark hover:bg-canvas-panel/80"
              )}
            >
              All ({memories.length})
            </button>
            {CATEGORIES.map((cat) => {
              const count = memories.filter((m) => m.category === cat.value).length;
              return (
                <button
                  key={cat.value}
                  onClick={() => setSelectedCategory(cat.value)}
                  className={cn(
                    "px-3 py-1 rounded-control text-meta transition-colors",
                    selectedCategory === cat.value
                      ? "bg-accent-600 text-white"
                      : "bg-canvas-panel dark:bg-canvas-dark-panel text-ink dark:text-ink-dark hover:bg-canvas-panel/80"
                  )}
                >
                  {cat.label} ({count})
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Memory list */}
      {settings?.memory_enabled && (
        <div className="space-y-2">
          {filteredMemories.length === 0 ? (
            <Card className="p-8 text-center">
              <p className="text-ink-secondary dark:text-ink-secondary-dark">
                No memories saved yet. Start a conversation and facts will be
                extracted automatically.
              </p>
            </Card>
          ) : (
            <div className="space-y-2">
              {filteredMemories.map((memory) => (
                <MemoryItemCard
                  key={memory.id}
                  item={memory}
                  categoryLabel={
                    CATEGORIES.find((c) => c.value === memory.category)?.label
                  }
                  onEdit={handleUpdateMemory}
                  onDelete={handleDeleteMemory}
                  onToggleActive={handleToggleActive}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {!settings?.memory_enabled && (
        <Card className="p-8 text-center">
          <p className="text-ink-secondary dark:text-ink-secondary-dark mb-4">
            Memory is currently disabled
          </p>
          <Button
            onClick={() => handleUpdateSettings({ memory_enabled: true })}
            variant="primary"
          >
            Enable Memory System
          </Button>
        </Card>
      )}
    </div>
  );
};
