"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { Button, Field, Select, TextInput } from "@/components/ui/field";
import { ApiError, problemFramingApi, workspaceApi } from "@/lib/api-client";
import type { Framework, FrameworkAnalysisResponse, FrameworkSectionSchema } from "@/lib/types";

function ProblemFramingPageInner() {
  const searchParams = useSearchParams();
  const engagementId = searchParams.get("engagement_id");

  const [framework, setFramework] = useState<Framework>("five_forces");
  const [sections, setSections] = useState<FrameworkSectionSchema[]>([]);
  const [templateError, setTemplateError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [entries, setEntries] = useState<Record<string, string[]>>({});
  const [draftEntry, setDraftEntry] = useState<Record<string, string>>({});
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [lastCreated, setLastCreated] = useState<FrameworkAnalysisResponse | null>(null);

  const [analyses, setAnalyses] = useState<FrameworkAnalysisResponse[]>([]);
  const [selected, setSelected] = useState<FrameworkAnalysisResponse | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [clearHistoryError, setClearHistoryError] = useState<string | null>(null);
  const [clearingHistory, setClearingHistory] = useState(false);

  function loadTemplate(fw: Framework) {
    setTemplateError(null);
    problemFramingApi
      .getTemplate(fw)
      .then((s) => {
        setSections(s);
        setEntries({});
        setDraftEntry({});
      })
      .catch((e) => setTemplateError(e instanceof ApiError ? e.detail : "Could not reach the backend."));
  }

  function refreshAnalyses() {
    problemFramingApi
      .listAnalyses()
      .then(setAnalyses)
      .catch((e) => setListError(e instanceof ApiError ? e.detail : "Could not reach the backend."));
  }

  async function handleClearHistory() {
    const confirmed = window.confirm("Are you sure you want to delete all analysis history?");
    if (!confirmed) return;

    setClearingHistory(true);
    setClearHistoryError(null);
    try {
      await problemFramingApi.clearHistory();
      setAnalyses([]);
      setSelected(null);
    } catch (e) {
      setClearHistoryError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setClearingHistory(false);
    }
  }

  useEffect(() => {
    loadTemplate(framework);
    refreshAnalyses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function addEntry(sectionKey: string) {
    const text = (draftEntry[sectionKey] ?? "").trim();
    if (!text) return;
    setEntries((prev) => ({ ...prev, [sectionKey]: [...(prev[sectionKey] ?? []), text] }));
    setDraftEntry((prev) => ({ ...prev, [sectionKey]: "" }));
  }

  function removeEntry(sectionKey: string, index: number) {
    setEntries((prev) => ({
      ...prev,
      [sectionKey]: (prev[sectionKey] ?? []).filter((_, i) => i !== index),
    }));
  }

  const filledSections = sections.filter((s) => (entries[s.key] ?? []).length > 0).length;
  const liveCompletionRatio = sections.length > 0 ? filledSections / sections.length : 0;

  async function submit() {
    setCreating(true);
    setCreateError(null);
    try {
      const res = await problemFramingApi.createAnalysis({ title, framework, entries });
      setLastCreated(res);
      setTitle("");
      setEntries({});
      refreshAnalyses();

      if (engagementId) {
        await workspaceApi.linkProblemFraming(engagementId, { analysis_id: res.analysis_id });
        window.location.href = `/dashboard/workspace/${engagementId}`;
        return;
      }
    } catch (e) {
      setCreateError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setCreating(false);
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

      {engagementId && (
        <p className="text-xs text-ledger bg-ink-2 border border-ledger/40 rounded-sm px-3 py-2 w-fit">
          Saving this analysis will link it back to your workspace engagement.
        </p>
      )}

      <div>
        <span className="text-[11px] uppercase tracking-wider text-ledger">Framing core / 05</span>
        <h1 className="font-display text-[28px] mt-1">Problem framing</h1>
        <p className="text-muted text-sm mt-1 max-w-xl">
          Guided strategy frameworks — Five Forces, SWOT — as structured section lists, so a user
          can&apos;t skip a dimension of the analysis.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-6">
        <Panel eyebrow="Inputs" title="Guided entry">
          <div className="flex flex-col gap-4">
            <Field label="Title">
              <TextInput value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>
            <Field label="Framework">
              <Select
                value={framework}
                onChange={(e) => {
                  const fw = e.target.value as Framework;
                  setFramework(fw);
                  loadTemplate(fw);
                }}
              >
                <option value="five_forces">Porter&apos;s Five Forces</option>
                <option value="swot">SWOT</option>
              </Select>
            </Field>

            {templateError && <p className="text-signal-down text-sm">{templateError}</p>}

            <div className="flex flex-col gap-3">
              {sections.map((s) => (
                <div key={s.key} className="border border-ink-border rounded-sm p-3 flex flex-col gap-2">
                  <div>
                    <span className="text-sm text-parchment font-medium">{s.label}</span>
                    <p className="text-xs text-muted mt-0.5">{s.guiding_question}</p>
                  </div>
                  {(entries[s.key] ?? []).length > 0 && (
                    <ul className="flex flex-col gap-1">
                      {(entries[s.key] ?? []).map((entry, i) => (
                        <li key={i} className="flex items-center justify-between gap-2 text-xs">
                          <span className="text-parchment">• {entry}</span>
                          <button
                            type="button"
                            onClick={() => removeEntry(s.key, i)}
                            className="text-signal-down hover:underline shrink-0"
                          >
                            remove
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="grid grid-cols-[1fr_auto] gap-2">
                    <TextInput
                      value={draftEntry[s.key] ?? ""}
                      onChange={(e) => setDraftEntry((prev) => ({ ...prev, [s.key]: e.target.value }))}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addEntry(s.key);
                        }
                      }}
                      placeholder="Add an observation…"
                      aria-label={`Add entry to ${s.label}`}
                    />
                    <Button variant="ghost" onClick={() => addEntry(s.key)} type="button">
                      + Add
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between bg-ink-2 border border-ink-border rounded-sm p-3">
              <span className="text-sm text-muted">Completion</span>
              <span className="font-data text-lg text-ledger tabular-nums">
                {(liveCompletionRatio * 100).toFixed(0)}%
              </span>
            </div>

            <Button onClick={submit} disabled={creating || !title || filledSections === 0} type="button">
              {creating ? "Saving…" : "Save analysis"}
            </Button>
            {createError && <p className="text-signal-down text-sm">{createError}</p>}
            {lastCreated && (
              <p className="text-xs text-signal-up">
                Saved — {(lastCreated.completion_ratio * 100).toFixed(0)}% of sections filled.
              </p>
            )}
          </div>
        </Panel>

        <div className="flex flex-col gap-6">
          <Panel
            eyebrow="History"
            title="Past analyses"
            headerAction={
              <Button
                variant="ghost"
                onClick={handleClearHistory}
                disabled={clearingHistory || analyses.length === 0}
                type="button"
              >
                {clearingHistory ? "Clearing…" : "Clear History"}
              </Button>
            }
          >
            {listError && <p className="text-signal-down text-sm mb-2">{listError}</p>}
            {clearHistoryError && <p className="text-signal-down text-sm mb-2">{clearHistoryError}</p>}
            {analyses.length > 0 ? (
              <div className="flex flex-col divide-y divide-ink-border">
                {analyses.map((a) => (
                  <button
                    key={a.analysis_id}
                    type="button"
                    onClick={() => setSelected(a)}
                    className="py-3 flex items-center justify-between gap-4 text-left hover:bg-ink-2 transition-colors -mx-2 px-2 rounded-sm"
                  >
                    <div>
                      <p className="text-sm text-parchment">{a.title}</p>
                      <p className="text-xs text-muted">
                        {a.framework.replace("_", " ")} · {new Date(a.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span className="text-sm text-ledger font-data">
                      {(a.completion_ratio * 100).toFixed(0)}%
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-muted text-sm">No analyses yet — save one to see it here.</p>
            )}
          </Panel>

          {selected && (
            <Panel eyebrow="Detail" title={selected.title}>
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between bg-ink-2 border border-ink-border rounded-sm p-3">
                  <span className="text-sm text-muted">Completion</span>
                  <span className="font-data text-lg text-ledger tabular-nums">
                    {(selected.completion_ratio * 100).toFixed(0)}%
                  </span>
                </div>
                {Object.entries(selected.entries).map(([key, values]) => (
                  <div key={key}>
                    <span className="text-[11px] uppercase tracking-wider text-muted">
                      {key.replace(/_/g, " ")}
                    </span>
                    <ul className="mt-1 flex flex-col gap-1">
                      {values.map((v, i) => (
                        <li key={i} className="text-sm text-parchment">
                          • {v}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ProblemFramingPage() {
  return (
    <Suspense fallback={<div className="text-muted text-sm">Loading…</div>}>
      <ProblemFramingPageInner />
    </Suspense>
  );
}
