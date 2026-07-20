"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Panel } from "@/components/ui/panel";
import { Button, Field, TextInput } from "@/components/ui/field";
import { evidenceResearchApi, workspaceApi, ApiError } from "@/lib/api-client";
import type { CitationResponse, DocumentResponse } from "@/lib/types";

function EvidenceResearchPageInner() {
  const searchParams = useSearchParams();
  const engagementId = searchParams.get("engagement_id");

  const [title, setTitle] = useState("");
  const [sourceLabel, setSourceLabel] = useState("");
  const [content, setContent] = useState("");
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [ingesting, setIngesting] = useState(false);

  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [documentsError, setDocumentsError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState("5");
  const [citations, setCitations] = useState<CitationResponse[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  function refreshDocuments() {
    evidenceResearchApi
      .listDocuments()
      .then(setDocuments)
      .catch((e) => setDocumentsError(e instanceof ApiError ? e.detail : "Could not reach the backend."));
  }

  useEffect(() => {
    refreshDocuments();
  }, []);

  async function ingest() {
    setIngesting(true);
    setIngestError(null);
    try {
      const doc = await evidenceResearchApi.ingestDocument({ title, source_label: sourceLabel, content });
      setTitle("");
      setSourceLabel("");
      setContent("");
      refreshDocuments();

      if (engagementId) {
        await workspaceApi.addEvidence(engagementId, { document_id: doc.document_id });
        window.location.href = `/dashboard/workspace/${engagementId}`;
        return;
      }
    } catch (e) {
      setIngestError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setIngesting(false);
    }
  }

  async function search() {
    setSearching(true);
    setSearchError(null);
    try {
      const res = await evidenceResearchApi.searchEvidence({ query, limit: Number(limit) });
      setCitations(res);
    } catch (e) {
      setSearchError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setSearching(false);
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
          Ingesting a document will link it back to your workspace engagement.
        </p>
      )}

      <div>
        <span className="text-[11px] uppercase tracking-wider text-ledger">Evidence core / 03</span>
        <h1 className="font-display text-[28px] mt-1">Evidence research</h1>
        <p className="text-muted text-sm mt-1 max-w-xl">
          Ingest source documents, then retrieve them by exact-excerpt citation via Postgres
          native full-text search — no vector database, no embedding API, no paraphrasing.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
        <Panel eyebrow="Inputs" title="Ingest a document">
          <div className="flex flex-col gap-4">
            <Field label="Title">
              <TextInput value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>
            <Field label="Source label" hint={'e.g. "Gartner 2026 report, p.14"'}>
              <TextInput value={sourceLabel} onChange={(e) => setSourceLabel(e.target.value)} />
            </Field>
            <Field label="Content">
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={8}
                className="bg-ink-0 border border-ink-border rounded-sm px-3 py-2 font-data text-sm text-parchment
                  focus:outline-none focus:border-ledger transition-colors resize-y"
              />
            </Field>
            <Button
              onClick={ingest}
              disabled={ingesting || !title || !sourceLabel || !content}
              type="button"
            >
              {ingesting ? "Ingesting…" : "Ingest document"}
            </Button>
            {ingestError && <p className="text-signal-down text-sm">{ingestError}</p>}
          </div>
        </Panel>

        <div className="flex flex-col gap-6">
          <Panel eyebrow="Search" title="Search evidence">
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-[1fr_100px] gap-2">
                <TextInput
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search terms"
                  aria-label="Search query"
                />
                <TextInput
                  value={limit}
                  onChange={(e) => setLimit(e.target.value)}
                  aria-label="Result limit"
                />
              </div>
              <Button onClick={search} disabled={searching || !query} type="button">
                {searching ? "Searching…" : "Search"}
              </Button>
              {searchError && <p className="text-signal-down text-sm">{searchError}</p>}

              {citations && (
                <div className="flex flex-col gap-3 mt-2">
                  {citations.length === 0 ? (
                    <p className="text-muted text-sm">No matching documents.</p>
                  ) : (
                    citations.map((c, i) => (
                      <div key={i} className="border border-ink-border rounded-sm p-3 flex flex-col gap-1.5">
                        <div className="flex items-baseline justify-between gap-2">
                          <span className="text-sm text-parchment font-medium">{c.document_title}</span>
                          <span className="text-xs text-muted font-data">
                            score {c.relevance_score.toFixed(3)}
                          </span>
                        </div>
                        <span className="text-xs text-ledger">{c.source_label}</span>
                        <div>
                          <span className="text-[11px] uppercase tracking-wider text-muted">
                            Exact excerpt
                          </span>
                          <p className="text-sm text-parchment leading-relaxed mt-0.5">
                            &ldquo;{c.excerpt}&rdquo;
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </Panel>

          <Panel eyebrow="Library" title="Ingested documents">
            {documentsError && <p className="text-signal-down text-sm mb-2">{documentsError}</p>}
            {documents.length > 0 ? (
              <div className="flex flex-col divide-y divide-ink-border">
                {documents.map((d) => (
                  <div key={d.document_id} className="py-3 flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm text-parchment">{d.title}</p>
                      <p className="text-xs text-muted">{d.source_label}</p>
                    </div>
                    <span className="text-xs text-muted font-data">
                      {new Date(d.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted text-sm">No documents ingested yet.</p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}

export default function EvidenceResearchPage() {
  return (
    <Suspense fallback={<div className="text-muted text-sm">Loading…</div>}>
      <EvidenceResearchPageInner />
    </Suspense>
  );
}
