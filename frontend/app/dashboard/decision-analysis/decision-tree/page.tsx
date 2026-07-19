"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { Button, Field, TextInput } from "@/components/ui/field";
import { FlagsCallout } from "@/components/ui/flags";
import { decisionAnalysisApi, ApiError } from "@/lib/api-client";
import type { EvaluateDecisionTreeResponse } from "@/lib/types";

interface OutcomeRow {
  name: string;
  probability: string;
  payoff: string;
}

interface OptionRow {
  name: string;
  outcomes: OutcomeRow[];
}

const DEFAULT_OPTIONS: OptionRow[] = [
  {
    name: "Expand into new market",
    outcomes: [
      { name: "high_demand", probability: "0.5", payoff: "1000000" },
      { name: "low_demand", probability: "0.5", payoff: "-200000" },
    ],
  },
  {
    name: "Stay in current market",
    outcomes: [
      { name: "high_demand", probability: "0.5", payoff: "100000" },
      { name: "low_demand", probability: "0.5", payoff: "100000" },
    ],
  },
];

export default function DecisionTreePage() {
  const [title, setTitle] = useState("Expand vs. stay — market entry decision");
  const [options, setOptions] = useState<OptionRow[]>(DEFAULT_OPTIONS);
  const [result, setResult] = useState<EvaluateDecisionTreeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function updateOptionName(index: number, name: string) {
    setOptions((prev) => prev.map((o, i) => (i === index ? { ...o, name } : o)));
  }

  function updateOutcome(optIndex: number, outIndex: number, patch: Partial<OutcomeRow>) {
    setOptions((prev) =>
      prev.map((o, i) =>
        i === optIndex
          ? { ...o, outcomes: o.outcomes.map((out, oi) => (oi === outIndex ? { ...out, ...patch } : out)) }
          : o,
      ),
    );
  }

  function addOutcome(optIndex: number) {
    setOptions((prev) =>
      prev.map((o, i) =>
        i === optIndex
          ? { ...o, outcomes: [...o.outcomes, { name: `outcome_${o.outcomes.length + 1}`, probability: "0", payoff: "0" }] }
          : o,
      ),
    );
  }

  function removeOutcome(optIndex: number, outIndex: number) {
    setOptions((prev) =>
      prev.map((o, i) =>
        i === optIndex ? { ...o, outcomes: o.outcomes.filter((_, oi) => oi !== outIndex) } : o,
      ),
    );
  }

  function addOption() {
    setOptions((prev) => [
      ...prev,
      {
        name: `Option ${prev.length + 1}`,
        outcomes: [
          { name: "outcome_a", probability: "0.5", payoff: "0" },
          { name: "outcome_b", probability: "0.5", payoff: "0" },
        ],
      },
    ]);
  }

  function removeOption(index: number) {
    setOptions((prev) => prev.filter((_, i) => i !== index));
  }

  function probabilitySum(option: OptionRow): number {
    return option.outcomes.reduce((s, o) => s + (Number(o.probability) || 0), 0);
  }

  const allProbabilitiesValid = options.every((o) => Math.abs(probabilitySum(o) - 1) < 0.001);

  async function runEvaluation() {
    setLoading(true);
    setError(null);
    try {
      const res = await decisionAnalysisApi.evaluateDecisionTree({
        title,
        options: options.map((o) => ({
          name: o.name,
          outcomes: o.outcomes.map((out) => ({
            name: out.name,
            probability: Number(out.probability),
            payoff: Number(out.payoff),
          })),
        })),
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  const chartData = result
    ? result.ranked_options.map(([name, emv]) => ({ name, emv }))
    : [];

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/"
        className="group inline-flex items-center gap-2 text-sm text-muted hover:text-parchment transition-colors w-fit"
      >
        <ArrowLeft size={16} className="transition-transform duration-200 group-hover:-translate-x-1" />
        Back to overview
      </Link>

      <div className="flex items-baseline justify-between">
        <div>
          <span className="text-[11px] uppercase tracking-wider text-ledger">Quant core / 02</span>
          <h1 className="font-display text-[28px] mt-1">Decision tree</h1>
          <p className="text-muted text-sm mt-1 max-w-xl">
            Expected monetary value across uncertain outcomes, plus the expected value of perfect
            information — the most you should pay for better data before deciding.
          </p>
        </div>
        <Link
          href="/dashboard/decision-analysis"
          className="text-sm text-muted hover:text-parchment transition-colors"
        >
          MCDA &amp; Monte Carlo →
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[460px_1fr] gap-6">
        <Panel eyebrow="Inputs" title="Options &amp; outcomes">
          <div className="flex flex-col gap-4">
            <Field label="Decision title">
              <TextInput value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>

            {options.map((option, oi) => {
              const sum = probabilitySum(option);
              const valid = Math.abs(sum - 1) < 0.001;
              return (
                <div key={oi} className="border border-ink-border rounded-sm p-3 flex flex-col gap-2">
                  <div className="grid grid-cols-[1fr_auto] gap-2 items-center">
                    <TextInput
                      value={option.name}
                      onChange={(e) => updateOptionName(oi, e.target.value)}
                      aria-label="Option name"
                    />
                    {options.length > 2 && (
                      <Button variant="ghost" onClick={() => removeOption(oi)} type="button">
                        Remove
                      </Button>
                    )}
                  </div>

                  <span className={`text-xs ${valid ? "text-signal-up" : "text-signal-down"}`}>
                    Outcome probabilities sum to {sum.toFixed(2)} {valid ? "✓" : "— must equal 1.00"}
                  </span>

                  {option.outcomes.map((outcome, outi) => (
                    <div key={outi} className="grid grid-cols-[1fr_70px_100px_auto] gap-2 items-center">
                      <TextInput
                        value={outcome.name}
                        onChange={(e) => updateOutcome(oi, outi, { name: e.target.value })}
                        aria-label="Outcome name"
                      />
                      <TextInput
                        value={outcome.probability}
                        onChange={(e) => updateOutcome(oi, outi, { probability: e.target.value })}
                        aria-label="Outcome probability"
                      />
                      <TextInput
                        value={outcome.payoff}
                        onChange={(e) => updateOutcome(oi, outi, { payoff: e.target.value })}
                        aria-label="Outcome payoff"
                      />
                      {option.outcomes.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeOutcome(oi, outi)}
                          className="text-muted hover:text-signal-down text-xs"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  ))}
                  <Button variant="ghost" onClick={() => addOutcome(oi)} type="button">
                    + Add outcome
                  </Button>
                </div>
              );
            })}

            <Button variant="ghost" onClick={addOption} type="button">
              + Add option
            </Button>

            <Button onClick={runEvaluation} disabled={loading || !allProbabilitiesValid} type="button">
              {loading ? "Evaluating…" : "Evaluate decision tree"}
            </Button>
            {!allProbabilitiesValid && (
              <p className="text-xs text-signal-down">
                Every option&apos;s outcome probabilities must sum to 1.00 before evaluating.
              </p>
            )}
            {error && <p className="text-signal-down text-sm">{error}</p>}
          </div>
        </Panel>

        <div className="flex flex-col gap-6">
          <Panel eyebrow="Output" title="Expected monetary value">
            {result ? (
              <div className="flex flex-col gap-6">
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-muted">Recommended</span>
                  <p className="font-display text-[22px] text-ledger mt-1">{result.recommended_option}</p>
                </div>

                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a333f" horizontal={false} />
                    <XAxis type="number" tick={{ fill: "#8B93A1", fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                    <YAxis type="category" dataKey="name" tick={{ fill: "#8B93A1", fontSize: 12 }} width={140} />
                    <Tooltip
                      contentStyle={{ background: "#141a23", border: "1px solid #2a333f" }}
                      formatter={(v: number) => [`$${v.toLocaleString()}`, "EMV"]}
                    />
                    <Bar dataKey="emv" radius={2}>
                      {chartData.map((d, i) => (
                        <Cell key={i} fill={i === 0 ? "#2FA89A" : d.emv >= 0 ? "#1E6B62" : "#C0604A"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>

                <div className="grid grid-cols-2 gap-4 border-t border-ink-border pt-4">
                  <Stat
                    label="EV with perfect info"
                    value={`$${result.expected_value_with_perfect_info.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                  />
                  <Stat
                    label="Value of perfect info (EVPI)"
                    value={`$${result.expected_value_of_perfect_information.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                  />
                </div>
                <p className="text-xs text-muted -mt-3">
                  EVPI is the most you should be willing to pay for research that would tell you the
                  true outcome in advance — if it costs more than this to find out, decide now instead.
                </p>

                {result.probability_breakeven && result.probability_breakeven.breakeven_probability !== null && (
                  <div className="border border-ledger/40 bg-ledger/10 rounded-sm p-4">
                    <span className="text-[11px] uppercase tracking-wider text-ledger">
                      Probability breakeven
                    </span>
                    <p className="text-sm text-parchment mt-2 leading-relaxed">
                      &quot;{result.probability_breakeven.option_a}&quot; beats &quot;
                      {result.probability_breakeven.option_b}&quot; only if the probability of &quot;
                      {result.probability_breakeven.outcome_name.replace(/_/g, " ")}&quot; exceeds{" "}
                      <span className="font-data text-ledger">
                        {(result.probability_breakeven.breakeven_probability * 100).toFixed(0)}%
                      </span>
                      .
                    </p>
                  </div>
                )}

                {result.flags.length > 0 && <FlagsCallout flags={result.flags} />}
              </div>
            ) : (
              <p className="text-muted text-sm">Evaluate the tree to see expected values.</p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
