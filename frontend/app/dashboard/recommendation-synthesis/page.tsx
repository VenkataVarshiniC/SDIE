"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { Button, Field, Select, TextInput } from "@/components/ui/field";
import {
  ApiError,
  decisionAnalysisApi,
  evidenceResearchApi,
  financialModelingApi,
  recommendationSynthesisApi,
  triggerBlobDownload,
  workspaceApi,
} from "@/lib/api-client";
import type {
  AnalysisSummary,
  CashFlowModelResponse,
  CitationResponse,
  EvidenceCitationSchema,
  QuantContext,
  RationaleResponse,
} from "@/lib/types";

function RecommendationSynthesisPageInner() {
  const searchParams = useSearchParams();
  const engagementId = searchParams.get("engagement_id");

  // --- create form state ---
  const [title, setTitle] = useState("");
  const [quantContext, setQuantContext] = useState<QuantContext>("decision_analysis");
  const [quantAnalysisId, setQuantAnalysisId] = useState("");
  const [recommendedOption, setRecommendedOption] = useState("");
  const [confidenceNote, setConfidenceNote] = useState("");
  const [attachedCitations, setAttachedCitations] = useState<EvidenceCitationSchema[]>([]);
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [financialModels, setFinancialModels] = useState<CashFlowModelResponse[]>([]);
  const [decisionAnalyses, setDecisionAnalyses] = useState<AnalysisSummary[]>([]);

  // --- evidence attach search ---
  const [evidenceQuery, setEvidenceQuery] = useState("");
  const [evidenceResults, setEvidenceResults] = useState<CitationResponse[]>([]);
  const [evidenceSearching, setEvidenceSearching] = useState(false);

  // --- list + detail ---
  const [rationales, setRationales] = useState<RationaleResponse[]>([]);
  const [selected, setSelected] = useState<RationaleResponse | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [clearHistoryError, setClearHistoryError] = useState<string | null>(null);
  const [clearingHistory, setClearingHistory] = useState(false);

  // --- override form ---
  const [overriddenBy, setOverriddenBy] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [newRecommendedOption, setNewRecommendedOption] = useState("");
  const [overrideError, setOverrideError] = useState<string | null>(null);
  const [overriding, setOverriding] = useState(false);

  // --- narrative ---
  const [narrative, setNarrative] = useState<string | null>(null);
  const [narrativeError, setNarrativeError] = useState<string | null>(null);
  const [generatingNarrative, setGeneratingNarrative] = useState(false);

  // --- one-pager ---
  const [downloadingOnePager, setDownloadingOnePager] = useState(false);
  const [onePagerError, setOnePagerError] = useState<string | null>(null);

  function refreshRationales() {
    recommendationSynthesisApi
      .listRationales()
      .then(setRationales)
      .catch((e) => setListError(e instanceof ApiError ? e.detail : "Could not reach the backend."));
  }

  async function handleClearHistory() {
    const confirmed = window.confirm("Are you sure you want to delete all analysis history?");
    if (!confirmed) return;

    setClearingHistory(true);
    setClearHistoryError(null);
    try {
      await recommendationSynthesisApi.clearHistory();
      setRationales([]);
      setSelected(null);
    } catch (e) {
      setClearHistoryError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setClearingHistory(false);
    }
  }

  useEffect(() => {
    refreshRationales();
    financialModelingApi.listCashFlowModels().then(setFinancialModels).catch(() => {});
    decisionAnalysisApi.listAnalyses().then(setDecisionAnalyses).catch(() => {});
  }, []);

  async function searchEvidenceToAttach() {
    setEvidenceSearching(true);
    try {
      const res = await evidenceResearchApi.searchEvidence({ query: evidenceQuery, limit: 5 });
      setEvidenceResults(res);
    } catch {
      setEvidenceResults([]);
    } finally {
      setEvidenceSearching(false);
    }
  }

  function attachCitation(c: CitationResponse) {
    setAttachedCitations((prev) =>
      prev.some((a) => a.document_id === c.document_id && a.excerpt === c.excerpt)
        ? prev
        : [
            ...prev,
            {
              document_id: c.document_id,
              document_title: c.document_title,
              source_label: c.source_label,
              excerpt: c.excerpt,
              relevance_score: c.relevance_score,
            },
          ],
    );
  }

  function removeAttachedCitation(index: number) {
    setAttachedCitations((prev) => prev.filter((_, i) => i !== index));
  }

  async function createRationale() {
    setCreating(true);
    setCreateError(null);
    try {
      const created = await recommendationSynthesisApi.createRationale({
        title,
        quant_context: quantContext,
        quant_analysis_id: quantAnalysisId,
        recommended_option: recommendedOption,
        confidence_note: confidenceNote,
        evidence_citations: attachedCitations,
      });
      setTitle("");
      setQuantAnalysisId("");
      setRecommendedOption("");
      setConfidenceNote("");
      setAttachedCitations([]);
      refreshRationales();

      if (engagementId) {
        await workspaceApi.linkRationale(engagementId, { rationale_id: created.rationale_id });
        window.location.href = `/dashboard/workspace/${engagementId}`;
        return;
      }
    } catch (e) {
      setCreateError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setCreating(false);
    }
  }

  function openDetail(r: RationaleResponse) {
    setSelected(r);
    setNarrative(null);
    setNarrativeError(null);
    setOnePagerError(null);
    setOverriddenBy("");
    setOverrideReason("");
    setNewRecommendedOption("");
  }

  async function submitOverride() {
    if (!selected) return;
    setOverriding(true);
    setOverrideError(null);
    try {
      const updated = await recommendationSynthesisApi.overrideRationale(selected.rationale_id, {
        overridden_by: overriddenBy,
        reason: overrideReason,
        new_recommended_option: newRecommendedOption,
      });
      setSelected(updated);
      setOverriddenBy("");
      setOverrideReason("");
      setNewRecommendedOption("");
      refreshRationales();
    } catch (e) {
      setOverrideError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setOverriding(false);
    }
  }

  async function generateNarrative() {
    if (!selected) return;
    setGeneratingNarrative(true);
    setNarrativeError(null);
    try {
      const res = await recommendationSynthesisApi.generateNarrative(selected.rationale_id);
      setNarrative(res.narrative);
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        setNarrativeError(
          `${e.detail} — narrative generation needs a free Groq API key configured on the backend.`,
        );
      } else {
        setNarrativeError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
      }
    } finally {
      setGeneratingNarrative(false);
    }
  }

  async function downloadOnePager() {
    if (!selected) return;
    setDownloadingOnePager(true);
    setOnePagerError(null);
    try {
      const blob = await recommendationSynthesisApi.downloadOnePager(selected.rationale_id);
      triggerBlobDownload(blob, `decision-memo-${selected.rationale_id}.pdf`);
    } catch (e) {
      setOnePagerError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setDownloadingOnePager(false);
    }
  }

  const analysisOptions =
    quantContext === "financial_modeling"
      ? financialModels.map((m) => ({ id: m.model_id, label: m.project_name }))
      : decisionAnalyses.map((a) => ({ id: a.analysis_id, label: a.title }));

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
          Creating this rationale will link it back to your workspace engagement.
        </p>
      )}

      <div>
        <span className="text-[11px] uppercase tracking-wider text-ledger">Synthesis core / 04</span>
        <h1 className="font-display text-[28px] mt-1">Recommendation synthesis</h1>
        <p className="text-muted text-sm mt-1 max-w-xl">
          Fuses a quant analysis with cited evidence into one auditable recommendation. Overrides
          are appended, never destructive — the original recommendation always stays visible.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-6">
        <Panel eyebrow="Inputs" title="Create rationale">
          <div className="flex flex-col gap-4">
            <Field label="Title">
              <TextInput value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>

            <Field label="Quant source">
              <Select
                value={quantContext}
                onChange={(e) => {
                  setQuantContext(e.target.value as QuantContext);
                  setQuantAnalysisId("");
                }}
              >
                <option value="decision_analysis">Decision analysis</option>
                <option value="financial_modeling">Financial modeling</option>
              </Select>
            </Field>

            <Field label="Source analysis" hint="Pulled from your prior analyses — run one first if empty">
              <Select value={quantAnalysisId} onChange={(e) => setQuantAnalysisId(e.target.value)}>
                <option value="">Select…</option>
                {analysisOptions.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.label}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Recommended option">
              <TextInput
                value={recommendedOption}
                onChange={(e) => setRecommendedOption(e.target.value)}
              />
            </Field>

            <Field label="Confidence note">
              <textarea
                value={confidenceNote}
                onChange={(e) => setConfidenceNote(e.target.value)}
                rows={3}
                className="bg-ink-0 border border-ink-border rounded-sm px-3 py-2 font-data text-sm text-parchment
                  focus:outline-none focus:border-ledger transition-colors resize-y"
              />
            </Field>

            <div className="flex flex-col gap-2 border border-ink-border rounded-sm p-3">
              <span className="text-sm text-muted">Attach evidence</span>
              <div className="grid grid-cols-[1fr_auto] gap-2">
                <TextInput
                  value={evidenceQuery}
                  onChange={(e) => setEvidenceQuery(e.target.value)}
                  placeholder="Search evidence…"
                  aria-label="Evidence search query"
                />
                <Button
                  variant="ghost"
                  onClick={searchEvidenceToAttach}
                  disabled={evidenceSearching || !evidenceQuery}
                  type="button"
                >
                  {evidenceSearching ? "…" : "Search"}
                </Button>
              </div>
              {evidenceResults.length > 0 && (
                <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto">
                  {evidenceResults.map((c, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => attachCitation(c)}
                      className="text-left text-xs border border-ink-border rounded-sm p-2 hover:border-ledger transition-colors"
                    >
                      <span className="text-ledger">{c.source_label}</span>
                      <p className="text-muted mt-0.5 line-clamp-2">&ldquo;{c.excerpt}&rdquo;</p>
                    </button>
                  ))}
                </div>
              )}
              {attachedCitations.length > 0 && (
                <div className="flex flex-col gap-1.5 mt-1">
                  <span className="text-[11px] uppercase tracking-wider text-muted">
                    Attached ({attachedCitations.length})
                  </span>
                  {attachedCitations.map((c, i) => (
                    <div key={i} className="flex items-center justify-between gap-2 text-xs">
                      <span className="text-parchment truncate">{c.source_label}</span>
                      <button
                        type="button"
                        onClick={() => removeAttachedCitation(i)}
                        className="text-signal-down hover:underline shrink-0"
                      >
                        remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <Button
              onClick={createRationale}
              disabled={creating || !title || !quantAnalysisId || !recommendedOption || !confidenceNote}
              type="button"
            >
              {creating ? "Creating…" : "Create rationale"}
            </Button>
            {createError && <p className="text-signal-down text-sm">{createError}</p>}
          </div>
        </Panel>

        <div className="flex flex-col gap-6">
          <Panel
            eyebrow="History"
            title="Rationales"
            headerAction={
              <Button
                variant="ghost"
                onClick={handleClearHistory}
                disabled={clearingHistory || rationales.length === 0}
                type="button"
              >
                {clearingHistory ? "Clearing…" : "Clear History"}
              </Button>
            }
          >
            {listError && <p className="text-signal-down text-sm mb-2">{listError}</p>}
            {clearHistoryError && <p className="text-signal-down text-sm mb-2">{clearHistoryError}</p>}
            {rationales.length > 0 ? (
              <div className="flex flex-col divide-y divide-ink-border">
                {rationales.map((r) => (
                  <button
                    key={r.rationale_id}
                    type="button"
                    onClick={() => openDetail(r)}
                    className="py-3 flex items-center justify-between gap-4 text-left hover:bg-ink-2 transition-colors -mx-2 px-2 rounded-sm"
                  >
                    <div>
                      <p className="text-sm text-parchment">{r.title}</p>
                      <p className="text-xs text-muted">{new Date(r.created_at).toLocaleString()}</p>
                    </div>
                    <span className="text-sm text-ledger font-data">{r.current_recommendation}</span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-muted text-sm">No rationales yet — create one to see it here.</p>
            )}
          </Panel>

          {selected && (
            <Panel eyebrow="Detail" title={selected.title}>
              <div className="flex flex-col gap-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-[11px] uppercase tracking-wider text-muted">
                      Original recommendation
                    </span>
                    <p className="text-sm text-parchment mt-0.5">{selected.recommended_option}</p>
                  </div>
                  <div>
                    <span className="text-[11px] uppercase tracking-wider text-ledger">
                      Current recommendation
                    </span>
                    <p className="text-sm text-parchment font-medium mt-0.5">
                      {selected.current_recommendation}
                    </p>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] uppercase tracking-wider text-muted">Confidence note</span>
                  <p className="text-sm text-parchment mt-0.5">{selected.confidence_note}</p>
                </div>

                {selected.evidence_citations.length > 0 && (
                  <div>
                    <span className="text-[11px] uppercase tracking-wider text-muted">Evidence</span>
                    <div className="flex flex-col gap-2 mt-1">
                      {selected.evidence_citations.map((c, i) => (
                        <div key={i} className="border border-ink-border rounded-sm p-2 text-sm">
                          <span className="text-ledger text-xs">{c.source_label}</span>
                          <p className="text-parchment mt-0.5">&ldquo;{c.excerpt}&rdquo;</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selected.overrides.length > 0 && (
                  <div>
                    <span className="text-[11px] uppercase tracking-wider text-muted">
                      Override history
                    </span>
                    <div className="flex flex-col gap-2 mt-1">
                      {selected.overrides.map((o, i) => (
                        <div key={i} className="border border-ink-border rounded-sm p-2 text-sm">
                          <div className="flex items-baseline justify-between">
                            <span className="text-parchment font-medium">
                              {o.new_recommended_option}
                            </span>
                            <span className="text-xs text-muted">
                              {new Date(o.overridden_at).toLocaleDateString()} · {o.overridden_by}
                            </span>
                          </div>
                          <p className="text-muted text-xs mt-0.5">{o.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="border-t border-ink-border pt-4 flex flex-col gap-2">
                  <span className="text-[11px] uppercase tracking-wider text-muted">
                    Override recommendation
                  </span>
                  <div className="grid grid-cols-2 gap-2">
                    <TextInput
                      value={overriddenBy}
                      onChange={(e) => setOverriddenBy(e.target.value)}
                      placeholder="Your name"
                    />
                    <TextInput
                      value={newRecommendedOption}
                      onChange={(e) => setNewRecommendedOption(e.target.value)}
                      placeholder="New recommendation"
                    />
                  </div>
                  <TextInput
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    placeholder="Reason (required)"
                  />
                  <Button
                    variant="ghost"
                    onClick={submitOverride}
                    disabled={overriding || !overriddenBy || !overrideReason || !newRecommendedOption}
                    type="button"
                  >
                    {overriding ? "Submitting…" : "Submit override"}
                  </Button>
                  {overrideError && <p className="text-signal-down text-sm">{overrideError}</p>}
                </div>

                <div className="border-t border-ink-border pt-4 flex flex-col gap-3">
                  <div className="flex gap-3">
                    <Button
                      variant="ghost"
                      onClick={generateNarrative}
                      disabled={generatingNarrative}
                      type="button"
                    >
                      {generatingNarrative ? "Generating…" : "Generate narrative"}
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={downloadOnePager}
                      disabled={downloadingOnePager}
                      type="button"
                    >
                      {downloadingOnePager ? "Preparing…" : "Download one-pager PDF"}
                    </Button>
                  </div>
                  {narrativeError && <p className="text-signal-down text-sm">{narrativeError}</p>}
                  {onePagerError && <p className="text-signal-down text-sm">{onePagerError}</p>}
                  {narrative && (
                    <p className="text-sm text-parchment leading-relaxed bg-ink-2 border border-ink-border rounded-sm p-3">
                      {narrative}
                    </p>
                  )}
                </div>
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

export default function RecommendationSynthesisPage() {
  return (
    <Suspense fallback={<div className="text-muted text-sm">Loading…</div>}>
      <RecommendationSynthesisPageInner />
    </Suspense>
  );
}
