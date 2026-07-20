"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { Button, Field, Select, TextInput } from "@/components/ui/field";
import { FlagsCallout } from "@/components/ui/flags";
import { financialModelingApi, workspaceApi, ApiError } from "@/lib/api-client";
import type {
  CashFlowModelResponse,
  EvaluateScenariosResponse,
  SensitivityResponse,
} from "@/lib/types";

interface CashFlowRow {
  period: number;
  amount: string;
}

interface ScenarioRow {
  name: string;
  probabilityPercent: string;
  rows: CashFlowRow[];
}

const DEFAULT_ROWS: CashFlowRow[] = [
  { period: 0, amount: "-1000000" },
  { period: 1, amount: "350000" },
  { period: 2, amount: "400000" },
  { period: 3, amount: "450000" },
  { period: 4, amount: "500000" },
];

const INDUSTRY_OPTIONS = [
  { value: "general", label: "General (total market average)" },
  { value: "software", label: "Software" },
  { value: "retail", label: "Retail" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "energy", label: "Energy" },
  { value: "healthcare", label: "Healthcare" },
];

const DEFAULT_SCENARIOS: ScenarioRow[] = [
  {
    name: "Bear",
    probabilityPercent: "25",
    rows: [
      { period: 0, amount: "-1000000" },
      { period: 1, amount: "200000" },
      { period: 2, amount: "250000" },
      { period: 3, amount: "280000" },
      { period: 4, amount: "300000" },
    ],
  },
  {
    name: "Base",
    probabilityPercent: "50",
    rows: DEFAULT_ROWS,
  },
  {
    name: "Bull",
    probabilityPercent: "25",
    rows: [
      { period: 0, amount: "-1000000" },
      { period: 1, amount: "500000" },
      { period: 2, amount: "600000" },
      { period: 3, amount: "700000" },
      { period: 4, amount: "800000" },
    ],
  },
];

function FinancialModelingPageInner() {
  const searchParams = useSearchParams();
  const engagementId = searchParams.get("engagement_id");

  const [projectName, setProjectName] = useState("Market expansion — EU");
  const [discountRate, setDiscountRate] = useState("9");
  const [industry, setIndustry] = useState("general");
  const [rows, setRows] = useState<CashFlowRow[]>(DEFAULT_ROWS);
  const [result, setResult] = useState<CashFlowModelResponse | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [scenarios, setScenarios] = useState<ScenarioRow[]>(DEFAULT_SCENARIOS);
  const [scenarioResult, setScenarioResult] = useState<EvaluateScenariosResponse | null>(null);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);

  function updateRow(index: number, field: keyof CashFlowRow, value: string) {
    setRows((prev) =>
      prev.map((row, i) =>
        i === index ? { ...row, [field]: field === "period" ? Number(value) : value } : row,
      ),
    );
  }

  function addRow() {
    setRows((prev) => [...prev, { period: prev.length, amount: "0" }]);
  }

  async function runModel() {
    setLoading(true);
    setError(null);
    try {
      const model = await financialModelingApi.createCashFlowModel({
        project_name: projectName,
        currency: "USD",
        discount_rate_percent: discountRate,
        industry,
        cash_flows: rows.map((r) => ({ period: r.period, amount: r.amount })),
      });
      setResult(model);

      if (engagementId) {
        await workspaceApi.linkFinancialModel(engagementId, { model_id: model.model_id });
        window.location.href = `/dashboard/workspace/${engagementId}`;
        return;
      }

      const lastRow = rows[rows.length - 1];
      if (lastRow) {
        const base = Number(lastRow.amount);
        const sens = await financialModelingApi.runSensitivity({
          currency: "USD",
          discount_rate_percent: discountRate,
          base_cash_flows: rows.map((r) => ({ period: r.period, amount: r.amount })),
          variable_name: `Year ${lastRow.period} cash flow`,
          variable_period: lastRow.period,
          low_amount: String(base * 0.7),
          base_amount: String(base),
          high_amount: String(base * 1.3),
        });
        setSensitivity(sens);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  function updateScenarioField(index: number, field: "name" | "probabilityPercent", value: string) {
    setScenarios((prev) => prev.map((s, i) => (i === index ? { ...s, [field]: value } : s)));
  }

  function updateScenarioRow(scenarioIndex: number, rowIndex: number, field: keyof CashFlowRow, value: string) {
    setScenarios((prev) =>
      prev.map((s, i) =>
        i === scenarioIndex
          ? {
              ...s,
              rows: s.rows.map((row, ri) =>
                ri === rowIndex
                  ? { ...row, [field]: field === "period" ? Number(value) : value }
                  : row,
              ),
            }
          : s,
      ),
    );
  }

  function addScenarioRow(scenarioIndex: number) {
    setScenarios((prev) =>
      prev.map((s, i) =>
        i === scenarioIndex ? { ...s, rows: [...s.rows, { period: s.rows.length, amount: "0" }] } : s,
      ),
    );
  }

  function addScenario() {
    setScenarios((prev) => [
      ...prev,
      {
        name: `Scenario ${prev.length + 1}`,
        probabilityPercent: "",
        rows: [
          { period: 0, amount: "-1000000" },
          { period: 1, amount: "400000" },
        ],
      },
    ]);
  }

  async function runScenarios() {
    setScenarioLoading(true);
    setScenarioError(null);
    try {
      const res = await financialModelingApi.evaluateScenarios({
        project_name: projectName,
        currency: "USD",
        discount_rate_percent: discountRate,
        scenarios: scenarios.map((s) => ({
          name: s.name,
          cash_flows: s.rows.map((r) => ({ period: r.period, amount: r.amount })),
          probability_percent: s.probabilityPercent.trim() === "" ? null : s.probabilityPercent,
        })),
      });
      setScenarioResult(res);
    } catch (e) {
      setScenarioError(e instanceof ApiError ? e.detail : "Could not reach the backend.");
    } finally {
      setScenarioLoading(false);
    }
  }

  const tornadoData = sensitivity
    ? [
        { label: "Low (-30%)", value: Number(sensitivity.npv_low) },
        { label: "Base", value: Number(sensitivity.npv_base) },
        { label: "High (+30%)", value: Number(sensitivity.npv_high) },
      ]
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

      {engagementId && (
        <p className="text-xs text-ledger bg-ink-2 border border-ledger/40 rounded-sm px-3 py-2 w-fit">
          Running this model will link it back to your workspace engagement.
        </p>
      )}

      <div>
        <span className="text-[11px] uppercase tracking-wider text-ledger">Quant core / 01</span>
        <h1 className="font-display text-[28px] mt-1">Financial modeling</h1>
        <p className="text-muted text-sm mt-1 max-w-xl">
          Discounted cash flow, computed deterministically. No language model touches these
          numbers.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
        <Panel eyebrow="Inputs" title="Cash flow model">
          <div className="flex flex-col gap-4">
            <Field label="Project name">
              <TextInput value={projectName} onChange={(e) => setProjectName(e.target.value)} />
            </Field>
            <Field label="Discount rate" hint="Annual, percent">
              <TextInput value={discountRate} onChange={(e) => setDiscountRate(e.target.value)} />
            </Field>
            <Field label="Industry" hint="Selects the benchmark WACC/IRR range for assumption flags">
              <Select value={industry} onChange={(e) => setIndustry(e.target.value)}>
                {INDUSTRY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </Select>
            </Field>

            <div className="flex flex-col gap-2">
              <span className="text-sm text-muted">Cash flows by period</span>
              {rows.map((row, i) => (
                <div key={i} className="grid grid-cols-[60px_1fr] gap-2">
                  <TextInput
                    value={row.period}
                    onChange={(e) => updateRow(i, "period", e.target.value)}
                    aria-label={`Period ${i}`}
                  />
                  <TextInput
                    value={row.amount}
                    onChange={(e) => updateRow(i, "amount", e.target.value)}
                    aria-label={`Amount for period ${row.period}`}
                  />
                </div>
              ))}
              <Button variant="ghost" onClick={addRow} type="button">
                + Add period
              </Button>
            </div>

            <Button onClick={runModel} disabled={loading} type="button">
              {loading ? "Computing…" : "Run model"}
            </Button>
            {error && <p className="text-signal-down text-sm">{error}</p>}
          </div>
        </Panel>

        <div className="flex flex-col gap-6">
          <Panel eyebrow="Output" title="Valuation">
            {result ? (
              <div className="flex flex-col gap-4">
                <div className="grid grid-cols-3 gap-6">
                  <Stat
                    label="Net present value"
                    value={formatMoney(result.npv, result.currency)}
                    tone={Number(result.npv) >= 0 ? "up" : "down"}
                  />
                  <Stat
                    label="Internal rate of return"
                    value={result.irr_percent ? `${Number(result.irr_percent).toFixed(1)}` : "—"}
                    suffix={result.irr_percent ? "%" : undefined}
                  />
                  <Stat
                    label="Payback period"
                    value={result.payback_period ? Number(result.payback_period).toFixed(1) : "—"}
                    suffix={result.payback_period ? "yrs" : undefined}
                  />
                </div>
                <p className="text-sm text-muted leading-relaxed border-t border-ink-border pt-3">
                  {describeValuation(result, discountRate)}
                </p>
                <FlagsCallout flags={result.flags} />
              </div>
            ) : (
              <p className="text-muted text-sm">Run the model to see valuation output.</p>
            )}
          </Panel>

          <Panel eyebrow="Output" title="Sensitivity — final-period cash flow">
            {sensitivity ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={tornadoData} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a333f" horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fill: "#8B93A1", fontSize: 11 }}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    tick={{ fill: "#8B93A1", fontSize: 12 }}
                    width={90}
                  />
                  <Tooltip
                    contentStyle={{ background: "#141a23", border: "1px solid #2a333f" }}
                    formatter={(v: number) => [`$${v.toLocaleString()}`, "NPV"]}
                  />
                  <Bar dataKey="value" radius={2}>
                    {tornadoData.map((d, i) => (
                      <Cell key={i} fill={d.value >= 0 ? "#4E9E6B" : "#C0604A"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted text-sm">Run the model to see the sensitivity range.</p>
            )}
          </Panel>
        </div>
      </div>

      <Panel eyebrow="Output" title="Scenario comparison">
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {scenarios.map((scenario, si) => (
              <div key={si} className="border border-ink-border rounded-sm p-3 flex flex-col gap-2">
                <div className="grid grid-cols-2 gap-2">
                  <TextInput
                    value={scenario.name}
                    onChange={(e) => updateScenarioField(si, "name", e.target.value)}
                    aria-label={`Scenario ${si} name`}
                  />
                  <TextInput
                    value={scenario.probabilityPercent}
                    onChange={(e) => updateScenarioField(si, "probabilityPercent", e.target.value)}
                    placeholder="Probability %"
                    aria-label={`Scenario ${si} probability`}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  {scenario.rows.map((row, ri) => (
                    <div key={ri} className="grid grid-cols-[44px_1fr] gap-1.5">
                      <TextInput
                        value={row.period}
                        onChange={(e) => updateScenarioRow(si, ri, "period", e.target.value)}
                        aria-label={`Scenario ${si} period ${ri}`}
                      />
                      <TextInput
                        value={row.amount}
                        onChange={(e) => updateScenarioRow(si, ri, "amount", e.target.value)}
                        aria-label={`Scenario ${si} amount ${ri}`}
                      />
                    </div>
                  ))}
                  <Button variant="ghost" onClick={() => addScenarioRow(si)} type="button">
                    + Add period
                  </Button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={addScenario} type="button">
              + Add scenario
            </Button>
            <Button onClick={runScenarios} disabled={scenarioLoading} type="button">
              {scenarioLoading ? "Comparing…" : "Compare scenarios"}
            </Button>
          </div>
          {scenarioError && <p className="text-signal-down text-sm">{scenarioError}</p>}

          {scenarioResult && (
            <div className="flex flex-col gap-4 border-t border-ink-border pt-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {scenarioResult.outcomes.map((o) => (
                  <div key={o.name} className="flex flex-col gap-3 border border-ink-border rounded-sm p-3">
                    <span className="text-sm text-parchment font-medium">{o.name}</span>
                    <Stat
                      label="NPV"
                      value={formatMoney(o.npv, "USD")}
                      tone={Number(o.npv) >= 0 ? "up" : "down"}
                    />
                    <Stat
                      label="IRR"
                      value={o.irr_percent ? Number(o.irr_percent).toFixed(1) : "—"}
                      suffix={o.irr_percent ? "%" : undefined}
                    />
                  </div>
                ))}
              </div>

              {scenarioResult.probability_weighted_npv !== null && (
                <div className="bg-ink-2 border border-ledger/40 rounded-sm p-4">
                  <span className="text-[11px] uppercase tracking-wider text-ledger">
                    Probability-weighted NPV
                  </span>
                  <p className="font-data text-3xl tabular-nums text-parchment mt-1">
                    {formatMoney(scenarioResult.probability_weighted_npv, "USD")}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}

function formatMoney(value: string, currency: string): string {
  const n = Number(value);
  const sign = n < 0 ? "-" : "";
  return `${sign}${currency} ${Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function describeValuation(result: CashFlowModelResponse, discountRatePercent: string): string {
  const npv = Number(result.npv);
  const irr = result.irr_percent !== null ? Number(result.irr_percent) : null;
  const discountRate = Number(discountRatePercent);
  const payback = result.payback_period !== null ? Number(result.payback_period) : null;

  const npvSentence =
    npv >= 0
      ? `At a ${discountRate}% discount rate, this project creates value: its NPV is positive, meaning the discounted cash inflows exceed the initial investment.`
      : `At a ${discountRate}% discount rate, this project destroys value: its NPV is negative, meaning the discounted cash inflows fall short of the initial investment.`;

  const irrSentence =
    irr === null
      ? " No IRR could be computed — the cash flows never change sign, so there's no breakeven discount rate to solve for."
      : irr > discountRate
        ? ` Its IRR of ${irr.toFixed(1)}% is above the ${discountRate}% discount rate, consistent with the positive NPV.`
        : ` Its IRR of ${irr.toFixed(1)}% is below the ${discountRate}% discount rate, consistent with the negative NPV.`;

  const paybackSentence =
    payback === null
      ? " The cumulative cash flow never turns positive within the modeled periods, so there's no payback period to report."
      : ` The initial investment is recovered in ${payback.toFixed(1)} years.`;

  return npvSentence + irrSentence + paybackSentence;
}

export default function FinancialModelingPage() {
  return (
    <Suspense fallback={<div className="text-muted text-sm">Loading…</div>}>
      <FinancialModelingPageInner />
    </Suspense>
  );
}
