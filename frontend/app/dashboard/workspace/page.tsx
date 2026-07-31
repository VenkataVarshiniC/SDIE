"use client";

import { useEffect, useState, type MouseEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Trash2 } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { Button, Field, TextInput } from "@/components/ui/field";
import { ApiError, workspaceApi } from "@/lib/api-client";
import type { EngagementResponse } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  framing: "Framing",
  evidence_gathering: "Evidence gathering",
  quant_analysis: "Quant analysis",
  synthesis: "Synthesis",
  complete: "Complete",
};

export default function WorkspacePage() {
  const router = useRouter();
  const [engagements, setEngagements] = useState<EngagementResponse[]>([]);
  const [listError, setListError] = useState<string | null>(null);
  const [clearHistoryError, setClearHistoryError] = useState<string | null>(null);
  const [clearingHistory, setClearingHistory] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  function refresh() {
    workspaceApi
      .listEngagements()
      .then(setEngagements)
      .catch((e) => setListError(e instanceof ApiError ? e.detail : "Could not reach the backend."));
  }

  useEffect(() => {
    refresh();
  }, []);

  async function createEngagement() {
    setCreating(true);
    setCreateError(null);
    try {
      const engagement = await workspaceApi.createEngagement({ title });
      setTitle("");
      router.push(`/dashboard/workspace/${engagement.engagement_id}`);
    } catch (e) {
      setCreateError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setCreating(false);
    }
  }

  async function handleClearHistory() {
    const confirmed = window.confirm("Are you sure you want to delete all analysis history?");
    if (!confirmed) return;

    setClearingHistory(true);
    setClearHistoryError(null);
    try {
      await workspaceApi.clearHistory();
      setEngagements([]);
    } catch (e) {
      setClearHistoryError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setClearingHistory(false);
    }
  }

  async function handleDeleteEngagement(e: MouseEvent, engagementId: string, title: string) {
    e.preventDefault();
    e.stopPropagation();

    const confirmed = window.confirm(`Delete "${title}"? This cannot be undone.`);
    if (!confirmed) return;

    setDeletingId(engagementId);
    setDeleteError(null);
    try {
      await workspaceApi.deleteEngagement(engagementId);
      setEngagements((prev) => prev.filter((eng) => eng.engagement_id !== engagementId));
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.detail : "Could not reach the backend.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/"
        className="group inline-flex items-center gap-2 text-sm text-muted hover:text-parchment transition-colors w-fit"
      >
        <ArrowLeft size={16} className="transition-transform duration-200 group-hover:-translate-x-1" />
        Back to overview
      </Link>

      <div>
        <span className="text-[11px] uppercase tracking-wider text-ledger">Orchestration / 00</span>
        <h1 className="font-display text-[28px] mt-1">Workspace</h1>
        <p className="text-muted text-sm mt-1 max-w-xl">
          An engagement walks a case from problem framing through evidence, quant analysis, and
          synthesis to a delivered recommendation — the five tools working as one platform.
        </p>
      </div>

      <Panel eyebrow="New" title="Start an engagement">
        <div className="grid grid-cols-[1fr_auto] gap-2">
          <TextInput
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Market entry approach — EU expansion"
          />
          <Button onClick={createEngagement} disabled={creating || !title} type="button">
            {creating ? "Creating…" : "New engagement"}
          </Button>
        </div>
        {createError && <p className="text-signal-down text-sm mt-2">{createError}</p>}
      </Panel>

      <Panel
        eyebrow="History"
        title="Engagements"
        headerAction={
          <Button
            variant="ghost"
            onClick={handleClearHistory}
            disabled={clearingHistory || engagements.length === 0}
            type="button"
          >
            {clearingHistory ? "Clearing…" : "Clear History"}
          </Button>
        }
      >
        {listError && <p className="text-signal-down text-sm mb-2">{listError}</p>}
        {clearHistoryError && <p className="text-signal-down text-sm mb-2">{clearHistoryError}</p>}
        {deleteError && <p className="text-signal-down text-sm mb-2">{deleteError}</p>}
        {engagements.length > 0 ? (
          <div className="flex flex-col divide-y divide-ink-border">
            {engagements.map((e) => (
              <Link
                key={e.engagement_id}
                href={`/dashboard/workspace/${e.engagement_id}`}
                className="py-3 flex items-center justify-between gap-4 hover:bg-ink-2 transition-colors -mx-2 px-2 rounded-sm"
              >
                <div>
                  <p className="text-sm text-parchment">{e.title}</p>
                  <p className="text-xs text-muted">{new Date(e.created_at).toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs uppercase tracking-wider text-ledger font-data">
                    {STATUS_LABEL[e.status] ?? e.status}
                  </span>
                  <button
                    type="button"
                    onClick={(evt) => handleDeleteEngagement(evt, e.engagement_id, e.title)}
                    disabled={deletingId === e.engagement_id}
                    aria-label={`Delete ${e.title}`}
                    className="text-muted hover:text-signal-down transition-colors disabled:opacity-40"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-muted text-sm">No engagements yet — start one above.</p>
        )}
      </Panel>
    </div>
  );
}
