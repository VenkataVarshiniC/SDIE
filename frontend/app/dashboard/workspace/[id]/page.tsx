"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Check, Download } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { Button } from "@/components/ui/field";
import { ApiError, recommendationSynthesisApi, triggerBlobDownload, workspaceApi } from "@/lib/api-client";
import type { EngagementResponse, RationaleResponse } from "@/lib/types";

interface StageConfig {
  key: string;
  label: string;
  description: string;
  linkedId: (e: EngagementResponse) => string | null;
  ctaHref: (engagementId: string) => string;
  ctaLabel: string;
  viewHref: (linkedId: string) => string;
}

const STAGES: StageConfig[] = [
  {
    key: "framing",
    label: "Problem framing",
    description: "Structure the question with a guided framework before analyzing anything.",
    linkedId: (e) => e.problem_framing_analysis_id,
    ctaHref: (id) => `/dashboard/problem-framing?engagement_id=${id}`,
    ctaLabel: "Frame the problem",
    viewHref: () => "/dashboard/problem-framing",
  },
  {
    key: "evidence",
    label: "Evidence",
    description: "Ingest and cite the source material this decision should be grounded in.",
    linkedId: (e) => e.evidence_document_ids[0] ?? null,
    ctaHref: (id) => `/dashboard/evidence-research?engagement_id=${id}`,
    ctaLabel: "Gather evidence",
    viewHref: () => "/dashboard/evidence-research",
  },
  {
    key: "quant",
    label: "Quant analysis",
    description: "Financial modeling and/or decision analysis — the deterministic core.",
    linkedId: (e) => e.financial_model_id ?? e.decision_analysis_id,
    ctaHref: (id) => `/dashboard/decision-analysis?engagement_id=${id}`,
    ctaLabel: "Run an analysis",
    viewHref: () => "/dashboard/decision-analysis",
  },
  {
    key: "synthesis",
    label: "Synthesis",
    description: "Fuse the quant output with cited evidence into one auditable recommendation.",
    linkedId: (e) => e.rationale_id,
    ctaHref: (id) => `/dashboard/recommendation-synthesis?engagement_id=${id}`,
    ctaLabel: "Create the rationale",
    viewHref: () => "/dashboard/recommendation-synthesis",
  },
];

export default function EngagementDetailPage() {
  const params = useParams<{ id: string }>();
  const engagementId = params.id;

  const [engagement, setEngagement] = useState<EngagementResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rationale, setRationale] = useState<RationaleResponse | null>(null);
  const [downloadingOnePager, setDownloadingOnePager] = useState(false);
  const [onePagerError, setOnePagerError] = useState<string | null>(null);

  useEffect(() => {
    workspaceApi
      .getEngagement(engagementId)
      .then(setEngagement)
      .catch((e) => setError(e instanceof ApiError ? e.detail : "Could not reach the backend."));
  }, [engagementId]);

  useEffect(() => {
    if (!engagement?.rationale_id) return;
    recommendationSynthesisApi
      .getRationale(engagement.rationale_id)
      .then(setRationale)
      .catch(() => {
        /* the stage card below still shows a "view artifact" link if this fails */
      });
  }, [engagement?.rationale_id]);

  async function downloadOnePager() {
    if (!engagement?.rationale_id) return;
    setDownloadingOnePager(true);
    setOnePagerError(null);
    try {
      const blob = await recommendationSynthesisApi.downloadOnePager(engagement.rationale_id);
      triggerBlobDownload(blob, `decision-memo-${engagement.rationale_id}.pdf`);
    } catch (e) {
      setOnePagerError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setDownloadingOnePager(false);
    }
  }

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        <p className="text-signal-down text-sm">{error}</p>
      </div>
    );
  }

  if (!engagement) {
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        <p className="text-muted text-sm">Loading…</p>
      </div>
    );
  }

  const isComplete = engagement.status === "complete";

  return (
    <div className="flex flex-col gap-6">
      <BackLink />

      <div>
        <span className="text-[11px] uppercase tracking-wider text-ledger">Engagement</span>
        <h1 className="font-display text-[28px] mt-1">{engagement.title}</h1>
        <p className="text-muted text-sm mt-1">
          Status:{" "}
          <span className="text-ledger font-data">
            {engagement.status.replace(/_/g, " ")}
          </span>
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {STAGES.map((stage, i) => {
          const linkedId = stage.linkedId(engagement);
          return (
            <Panel key={stage.key} eyebrow={`Stage 0${i + 1}`} title={stage.label}>
              <div className="flex items-center justify-between gap-4">
                <p className="text-sm text-muted max-w-md">{stage.description}</p>
                {linkedId ? (
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="flex items-center gap-1.5 text-signal-up text-sm">
                      <Check size={16} /> Linked
                    </span>
                    <Link
                      href={stage.viewHref(linkedId)}
                      className="text-sm text-ledger hover:underline"
                    >
                      View artifact →
                    </Link>
                  </div>
                ) : (
                  <Link
                    href={stage.ctaHref(engagement.engagement_id)}
                    className="shrink-0 px-4 py-2 rounded-sm text-sm font-medium bg-ledger-dim text-parchment hover:bg-ledger transition-colors"
                  >
                    {stage.ctaLabel}
                  </Link>
                )}
              </div>
            </Panel>
          );
        })}

        <Panel eyebrow="Stage 05" title="Complete">
          {!isComplete && (
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm text-muted max-w-md">
                Reached once a recommendation exists and is backed by at least one quant analysis.
              </p>
              <span className="text-xs text-muted shrink-0">Not yet reached</span>
            </div>
          )}

          {isComplete && rationale && (
            <div className="flex flex-col gap-4">
              <span className="flex items-center gap-1.5 text-signal-up text-sm">
                <Check size={16} /> Complete
              </span>

              <div className="bg-ink-2 border border-ledger/40 rounded-sm p-4 flex flex-col gap-3">
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-ledger">
                    Final recommendation
                  </span>
                  <p className="font-display text-[22px] text-parchment mt-1">
                    {rationale.current_recommendation}
                  </p>
                  {rationale.current_recommendation !== rationale.recommended_option && (
                    <p className="text-xs text-muted mt-1">
                      Original quant-derived recommendation was{" "}
                      <span className="text-parchment">{rationale.recommended_option}</span>,
                      overridden by {rationale.overrides[rationale.overrides.length - 1]?.overridden_by}.
                    </p>
                  )}
                </div>

                <div>
                  <span className="text-[11px] uppercase tracking-wider text-muted">Why</span>
                  <p className="text-sm text-parchment mt-0.5">{rationale.confidence_note}</p>
                </div>

                {rationale.evidence_citations.length > 0 && (
                  <div>
                    <span className="text-[11px] uppercase tracking-wider text-muted">
                      Evidence ({rationale.evidence_citations.length})
                    </span>
                    <div className="flex flex-col gap-1.5 mt-1">
                      {rationale.evidence_citations.map((c, i) => (
                        <p key={i} className="text-xs text-muted">
                          &ldquo;{c.excerpt}&rdquo; — <span className="text-ledger">{c.source_label}</span>
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-3 pt-1">
                  <Button
                    variant="ghost"
                    onClick={downloadOnePager}
                    disabled={downloadingOnePager}
                    type="button"
                  >
                    <span className="inline-flex items-center gap-1.5">
                      <Download size={14} />
                      {downloadingOnePager ? "Preparing…" : "Download one-pager PDF"}
                    </span>
                  </Button>
                  <Link
                    href="/dashboard/recommendation-synthesis"
                    className="text-sm text-ledger hover:underline"
                  >
                    View full details →
                  </Link>
                </div>
                {onePagerError && <p className="text-signal-down text-xs">{onePagerError}</p>}
              </div>
            </div>
          )}

          {isComplete && !rationale && (
            <p className="text-muted text-sm">Loading final analysis…</p>
          )}
        </Panel>
      </div>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/dashboard/workspace"
      className="group inline-flex items-center gap-2 text-sm text-muted hover:text-parchment transition-colors w-fit"
    >
      <ArrowLeft size={16} className="transition-transform duration-200 group-hover:-translate-x-1" />
      Back to engagements
    </Link>
  );
}
