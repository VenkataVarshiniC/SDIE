"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Panel } from "@/components/ui/panel";
import { Button, Field, TextInput } from "@/components/ui/field";
import { decisionAnalysisApi, ApiError } from "@/lib/api-client";
import type { AnalysisSummary, RankOptionsResponse } from "@/lib/types";

interface CriterionRow {
  name: string;
  weight: string;
  higherIsBetter: boolean;
}

interface OptionRow {
  name: string;
  scores: Record<string, string>;
}

const DEFAULT_CRITERIA: CriterionRow[] = [
  { name: "cost", weight: "0.4", higherIsBetter: false },
  { name: "speed_to_market", weight: "0.3", higherIsBetter: true },
  { name: "strategic_fit", weight: "0.3", higherIsBetter: true },
];

const DEFAULT_OPTIONS: OptionRow[] = [
  { name: "Build in-house", scores: { cost: "8", speed_to_market: "3", strategic_fit: "9" } },
  { name: "Acquire competitor", scores: { cost: "3", speed_to_market: "9", strategic_fit: "6" } },
  { name: "Partner / JV", scores: { cost: "6", speed_to_market: "7", strategic_fit: "5" } },
];

export default function DecisionAnalysisPage() {
  const [title, setTitle] = useState("Market entry approach");
  const [criteria, setCriteria] = useState<CriterionRow[]>(DEFAULT_CRITERIA);
  const [options, setOptions] = useState<OptionRow[]>(DEFAULT_OPTIONS);
  const [result, setResult] = useState<RankOptionsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisSummary[]>([]);

  useEffect(() => {
    decisionAnalysisApi
      .listAnalyses()
      .then(setRecentAnalyses)
      .catch(() => {
        /* history is a nice-to-have; a failed fetch here shouldn't block the page */
      });
  }, []);

  const weightSum = criteria.reduce((s, c) => s + (Number(c.weight) || 0), 0);

  function updateCriterionWeight(index: number, weight: string) {
    setCriteria((prev) => prev.map((c, i) => (i === index ? { ...c, weight } : c)));
  }

  function updateScore(optionIndex: number, criterionName: string, value: string) {
    setOptions((prev) =>
      prev.map((o, i) =>
        i === optionIndex ? { ...o, scores: { ...o.scores, [criterionName]: value } } : o,
      ),
    );
  }

  async function runRanking() {
    setLoading(true);
    setError(null);
    try {
      const res = await decisionAnalysisApi.rankOptions({
        title,
        criteria: criteria.map((c) => ({
          name: c.name,
          weight: Number(c.weight),
          higher_is_better: c.higherIsBetter,
        })),
        options: options.map((o) => ({
          name: o.name,
          scores: Object.fromEntries(Object.entries(o.scores).map(([k, v]) => [k, Number(v)])),
        })),
      });
      setResult(res);
      decisionAnalysisApi.listAnalyses().then(setRecentAnalyses).catch(() => {});
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  const chartData = result
    ? result.rankings.map((r) => ({ name: r.option, score: r.weighted_score }))
    : [];

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/"
        className="group inline-flex items-center gap-2 text-sm text-muted hover:text-parchment transition-colors w-fit"
      >
        <ArrowLeft
          size={16}
          className="transition-transform duration-200 group-hover:-translate-x-1"
        />
        Back to overview
      </Link>

      <div>
        <span className="text-[11px] uppercase tracking-wider text-ledger">Quant core / 02</span>
        <h1 className="font-display text-[28px] mt-1">Decision analysis</h1>
        <p className="text-muted text-sm mt-1 max-w-xl">
          Weighted-sum MCDA. Every score is min-max normalized per criterion — traceable, not a
          black box.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-6">
        <Panel eyebrow="Inputs" title="Criteria &amp; options">
          <div className="flex flex-col gap-5">
            <Field label="Decision title">
              <TextInput value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>

            <div className="flex flex-col gap-2">
              <span className="text-sm text-muted">
                Criteria weights{" "}
                <span className={weightSum === 1 ? "text-signal-up" : "text-signal-down"}>
                  (sum: {weightSum.toFixed(2)})
                </span>
              </span>
              {criteria.map((c, i) => (
                <div key={c.name} className="grid grid-cols-[1fr_90px] gap-2 items-center">
                  <span className="text-sm text-parchment">
                    {c.name}
                    <span className="text-muted"> ({c.higherIsBetter ? "higher better" : "lower better"})</span>
                  </span>
                  <TextInput
                    value={c.weight}
                    onChange={(e) => updateCriterionWeight(i, e.target.value)}
                    aria-label={`Weight for ${c.name}`}
                  />
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-3">
              <span className="text-sm text-muted">Option scores (1–10 raw scale)</span>
              {options.map((o, i) => (
                <div key={o.name} className="border border-ink-border rounded-sm p-3 flex flex-col gap-2">
                  <span className="text-sm text-parchment">{o.name}</span>
                  <div className="grid grid-cols-3 gap-2">
                    {criteria.map((c) => (
                      <TextInput
                        key={c.name}
                        value={o.scores[c.name] ?? ""}
                        onChange={(e) => updateScore(i, c.name, e.target.value)}
                        aria-label={`${o.name} score for ${c.name}`}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <Button onClick={runRanking} disabled={loading || weightSum !== 1} type="button">
              {loading ? "Ranking…" : "Rank options"}
            </Button>
            {weightSum !== 1 && (
              <p className="text-xs text-signal-down">Weights must sum to exactly 1.00</p>
            )}
            {error && <p className="text-signal-down text-sm">{error}</p>}
          </div>
        </Panel>

        <Panel eyebrow="Output" title="Ranking">
          {result ? (
            <div className="flex flex-col gap-6">
              <div>
                <span className="text-[11px] uppercase tracking-wider text-muted">Recommended</span>
                <p className="font-display text-[22px] text-ledger mt-1">
                  {result.recommended_option}
                </p>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a333f" horizontal={false} />
                  <XAxis type="number" domain={[0, 1]} tick={{ fill: "#8B93A1", fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: "#8B93A1", fontSize: 12 }} width={130} />
                  <Tooltip
                    contentStyle={{ background: "#141a23", border: "1px solid #2a333f" }}
                    formatter={(v: number) => [v.toFixed(3), "Weighted score"]}
                  />
                  <Bar dataKey="score" radius={2}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? "#2FA89A" : "#1E6B62"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>

              <div className="text-xs text-muted">
                Normalized scores are min-max per criterion across the option set — a score of 1.0
                means that option was the best on that criterion among those compared, not an
                absolute benchmark.
              </div>

              <p className="text-sm text-muted leading-relaxed border-t border-ink-border pt-3">
                {describeRanking(result)}
              </p>
            </div>
          ) : (
            <p className="text-muted text-sm">Rank options to see the recommendation.</p>
          )}
        </Panel>
      </div>

      <Panel eyebrow="History" title="Recent analyses">
        {recentAnalyses.length > 0 ? (
          <div className="flex flex-col divide-y divide-ink-border">
            {recentAnalyses.map((a) => (
              <div key={a.analysis_id} className="py-3 flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm text-parchment">{a.title}</p>
                  <p className="text-xs text-muted">
                    {a.method} · {new Date(a.created_at).toLocaleString()}
                  </p>
                </div>
                <span className="text-sm text-ledger font-data">{a.recommended_option}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted text-sm">No analyses yet — run a ranking above to see it here.</p>
        )}
      </Panel>
    </div>
  );
}

function describeRanking(result: RankOptionsResponse): string {
  const [top, second] = result.rankings;
  if (!top) return "";

  const marginSentence = second
    ? `It leads "${second.option}" by a weighted-score margin of ${(top.weighted_score - second.weighted_score).toFixed(2)} (on a 0–1 scale).`
    : "It was the only option scored.";

  const drivingCriteria = Object.entries(top.normalized_scores)
    .filter(([, score]) => score >= 0.75)
    .map(([name]) => name.replace(/_/g, " "));

  const drivingSentence =
    drivingCriteria.length > 0
      ? ` This is driven mainly by its strength on ${drivingCriteria.join(" and ")}.`
      : " No single criterion dominates — its lead comes from being solidly competitive across the board.";

  return `"${top.option}" is the recommended option. ${marginSentence}${drivingSentence} A narrow margin is worth re-examining the criteria weights before committing; a wide one is a more robust recommendation.`;
}
