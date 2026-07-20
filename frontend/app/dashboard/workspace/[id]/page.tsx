"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Check } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { ApiError, workspaceApi } from "@/lib/api-client";
import type { EngagementResponse } from "@/lib/types";

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

  useEffect(() => {
    workspaceApi
      .getEngagement(engagementId)
      .then(setEngagement)
      .catch((e) => setError(e instanceof ApiError ? e.detail : "Could not reach the backend."));
  }, [engagementId]);

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
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-muted max-w-md">
              Reached once a recommendation exists and is backed by at least one quant analysis.
            </p>
            {isComplete ? (
              <span className="flex items-center gap-1.5 text-signal-up text-sm shrink-0">
                <Check size={16} /> Complete
              </span>
            ) : (
              <span className="text-xs text-muted shrink-0">Not yet reached</span>
            )}
          </div>
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
