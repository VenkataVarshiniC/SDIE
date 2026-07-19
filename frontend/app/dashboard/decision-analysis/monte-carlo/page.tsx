"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { Button, Field, Select, TextInput } from "@/components/ui/field";
import { decisionAnalysisApi, ApiError } from "@/lib/api-client";
import type { DistributionKind, MonteCarloResponse } from "@/lib/types";

interface VariableRow {
  name: string;
  kind: DistributionKind;
  params: string[]; // kept as strings for controlled inputs, parsed to numbers on submit
}

const PARAM_LABELS: Record<DistributionKind, string[]> = {
  normal: ["Mean", "Std dev"],
  triangular: ["Min", "Mode", "Max"],
  uniform: ["Min", "Max"],
  lognormal: ["Mean of log", "Std dev of log"],
};

function defaultParamsFor(kind: DistributionKind): string[] {
  switch (kind) {
    case "normal":
      return ["600000", "50000"];
    case "triangular":
      return ["400000", "500000", "650000"];
    case "uniform":
      return ["400000", "600000"];
    case "lognormal":
      return ["13", "0.2"];
  }
}

const DEFAULT_VARIABLES: VariableRow[] = [
  { name: "revenue_north_america", kind: "normal", params: ["600000", "50000"] },
  { name: "revenue_europe", kind: "normal", params: ["400000", "40000"] },
];

export default function MonteCarloPage() {
  const [title, setTitle] = useState("New product launch — payoff simulation");
  const [variables, setVariables] = useState<VariableRow[]>(DEFAULT_VARIABLES);
  const [fixedCosts, setFixedCosts] = useState("800000");
  const [iterations, setIterations] = useState("10000");
  const [seed, setSeed] = useState("42");
  const [result, setResult] = useState<MonteCarloResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function updateVariable(index: number, patch: Partial<VariableRow>) {
    setVariables((prev) => prev.map((v, i) => (i === index ? { ...v, ...patch } : v)));
  }

  function updateVariableKind(index: number, kind: DistributionKind) {
    setVariables((prev) =>
      prev.map((v, i) => (i === index ? { ...v, kind, params: defaultParamsFor(kind) } : v)),
    );
  }

  function updateParam(varIndex: number, paramIndex: number, value: string) {
    setVariables((prev) =>
      prev.map((v, i) =>
        i === varIndex
          ? { ...v, params: v.params.map((p, pi) => (pi === paramIndex ? value : p)) }
          : v,
      ),
    );
  }

  function addVariable() {
    setVariables((prev) => [
      ...prev,
      { name: `variable_${prev.length + 1}`, kind: "normal", params: defaultParamsFor("normal") },
    ]);
  }

  function removeVariable(index: number) {
    setVariables((prev) => prev.filter((_, i) => i !== index));
  }

  async function runSimulation() {
    setLoading(true);
    setError(null);
    try {
      const res = await decisionAnalysisApi.runMonteCarlo({
        title,
        variables: variables.map((v) => ({
          name: v.name,
          kind: v.kind,
          params: v.params.map(Number),
        })),
        fixed_costs: Number(fixedCosts),
        iterations: Number(iterations),
        seed: Number(seed),
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  const histogramData = result
    ? result.histogram.map((bin) => ({
        label: `${(bin.bin_start / 1000).toFixed(0)}k`,
        count: bin.count,
      }))
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
          <h1 className="font-display text-[28px] mt-1">Monte Carlo simulation</h1>
          <p className="text-muted text-sm mt-1 max-w-xl">
            Simulates payoff under uncertainty by sampling each variable&apos;s distribution
            thousands of times — the same computation as MCDA and decision trees, just quantifying
            a full outcome distribution instead of a single expected value.
          </p>
        </div>
        <Link
          href="/dashboard/decision-analysis"
          className="text-sm text-muted hover:text-parchment transition-colors"
        >
          MCDA &amp; decision trees →
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-6">
        <Panel eyebrow="Inputs" title="Payoff model">
          <div className="flex flex-col gap-5">
            <Field label="Simulation title">
              <TextInput value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>

            <div className="flex flex-col gap-3">
              <span className="text-sm text-muted">
                Uncertain variables — payoff = sum(variables) − fixed costs
              </span>
              {variables.map((v, i) => (
                <div key={i} className="border border-ink-border rounded-sm p-3 flex flex-col gap-2">
                  <div className="grid grid-cols-[1fr_auto] gap-2 items-center">
                    <TextInput
                      value={v.name}
                      onChange={(e) => updateVariable(i, { name: e.target.value })}
                      aria-label="Variable name"
                    />
                    {variables.length > 1 && (
                      <Button variant="ghost" onClick={() => removeVariable(i)} type="button">
                        Remove
                      </Button>
                    )}
                  </div>
                  <Select
                    value={v.kind}
                    onChange={(e) => updateVariableKind(i, e.target.value as DistributionKind)}
                    aria-label="Distribution kind"
                  >
                    <option value="normal">Normal</option>
                    <option value="triangular">Triangular</option>
                    <option value="uniform">Uniform</option>
                    <option value="lognormal">Lognormal</option>
                  </Select>
                  <div className="grid grid-cols-3 gap-2">
                    {PARAM_LABELS[v.kind].map((label, pi) => (
                      <Field key={label} label={label}>
                        <TextInput
                          value={v.params[pi] ?? ""}
                          onChange={(e) => updateParam(i, pi, e.target.value)}
                        />
                      </Field>
                    ))}
                  </div>
                </div>
              ))}
              <Button variant="ghost" onClick={addVariable} type="button">
                + Add variable
              </Button>
            </div>

            <Field label="Fixed costs" hint="Subtracted from the sum of sampled variables">
              <TextInput value={fixedCosts} onChange={(e) => setFixedCosts(e.target.value)} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Iterations">
                <TextInput value={iterations} onChange={(e) => setIterations(e.target.value)} />
              </Field>
              <Field label="Seed" hint="Same seed = reproducible result">
                <TextInput value={seed} onChange={(e) => setSeed(e.target.value)} />
              </Field>
            </div>

            <Button onClick={runSimulation} disabled={loading} type="button">
              {loading ? "Simulating…" : "Run simulation"}
            </Button>
            {error && <p className="text-signal-down text-sm">{error}</p>}
          </div>
        </Panel>

        <div className="flex flex-col gap-6">
          <Panel eyebrow="Output" title="Payoff distribution">
            {result ? (
              <div className="flex flex-col gap-6">
                <div className="grid grid-cols-3 gap-4">
                  <Stat
                    label="Mean payoff"
                    value={result.mean.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    tone={result.mean >= 0 ? "up" : "down"}
                  />
                  <Stat
                    label="Std deviation"
                    value={result.std_dev.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  />
                  <Stat
                    label="P(payoff < 0)"
                    value={(result.probability_negative * 100).toFixed(1)}
                    suffix="%"
                    tone={result.probability_negative > 0.2 ? "down" : "neutral"}
                  />
                </div>
                <div className="grid grid-cols-3 gap-4 border-t border-ink-border pt-4">
                  <Stat
                    label="P5"
                    value={result.percentile_5.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  />
                  <Stat
                    label="P50 (median)"
                    value={result.percentile_50.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  />
                  <Stat
                    label="P95"
                    value={result.percentile_95.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  />
                </div>

                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={histogramData} margin={{ left: 10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a333f" vertical={false} />
                    <XAxis
                      dataKey="label"
                      tick={{ fill: "#8B93A1", fontSize: 10 }}
                      interval={Math.floor(histogramData.length / 8)}
                    />
                    <YAxis tick={{ fill: "#8B93A1", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ background: "#141a23", border: "1px solid #2a333f" }}
                      formatter={(v: number) => [v, "Simulations in bin"]}
                    />
                    <Bar dataKey="count" fill="#2FA89A" radius={2} />
                  </BarChart>
                </ResponsiveContainer>

                <p className="text-xs text-muted">
                  {result.iterations.toLocaleString()} iterations, seed {result.seed} — rerun with
                  the same seed to get this exact distribution back.
                </p>
              </div>
            ) : (
              <p className="text-muted text-sm">
                Run the simulation to see the payoff distribution.
              </p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
