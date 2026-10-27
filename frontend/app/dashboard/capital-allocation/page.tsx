"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowLeft, Download } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button, Field, TextInput } from "@/components/ui/field";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { ApiError, financialModelingApi, triggerBlobDownload } from "@/lib/api-client";
import { formatCompactUsd, formatUsd } from "@/lib/finance-format";
import type {
  AnalyzeOperatingForecastRequest,
  AnalyzeOperatingForecastResponse,
  CapitalAllocationRequest,
  CapitalAllocationResponse,
  InvestmentOpportunityInput,
  OperatingForecastAssumptions,
} from "@/lib/types";

const INVESTMENTS: InvestmentOpportunityInput[] = [
  {
    investment_id: "data-foundation",
    name: "Data foundation modernization",
    initial_capital: "2500000",
    future_cash_flows: ["450000", "750000", "1050000", "1350000", "1550000"],
    downside_cash_flows: ["300000", "500000", "700000", "900000", "1050000"],
    risk_assumption:
      "Migration may run one quarter late; downside assumes lower productivity savings and delayed platform reuse.",
    strategic_priority: 5,
    dependencies: [],
  },
  {
    investment_id: "enterprise-ai",
    name: "Enterprise AI workflow module",
    initial_capital: "4500000",
    future_cash_flows: ["1200000", "1700000", "2400000", "3100000", "3700000"],
    downside_cash_flows: ["600000", "900000", "1300000", "1700000", "2000000"],
    risk_assumption:
      "Enterprise adoption and model-inference costs are the principal uncertainties; downside assumes a slower sales ramp.",
    strategic_priority: 5,
    dependencies: ["data-foundation"],
  },
  {
    investment_id: "international-self-serve",
    name: "International self-serve expansion",
    initial_capital: "3000000",
    future_cash_flows: ["700000", "1100000", "1550000", "1950000", "2250000"],
    downside_cash_flows: ["250000", "500000", "800000", "1050000", "1250000"],
    risk_assumption:
      "Localization, customer acquisition cost, and conversion are uncertain; downside assumes two years of slower penetration.",
    strategic_priority: 4,
    dependencies: [],
  },
];

function forecastAssumptions(
  discountRate: string,
  name: string,
  growth: string[],
  grossMargin: string,
  opex: string,
  capex: string,
): OperatingForecastAssumptions {
  return {
    project_name: name,
    currency: "USD",
    base_revenue: "12000000",
    initial_investment: "4500000",
    revenue_growth_percent_by_year: growth,
    gross_margin_percent: grossMargin,
    operating_expense_percent_of_revenue: opex,
    depreciation_amortization_percent_of_revenue: "3",
    tax_rate_percent: "25",
    capital_expenditure_percent_of_revenue: capex,
    working_capital_percent_of_revenue: "8",
    discount_rate_percent: discountRate,
  };
}

export default function CapitalAllocationPage() {
  const [capitalBudget, setCapitalBudget] = useState("8500000");
  const [discountRate, setDiscountRate] = useState("9.34");
  const [allocation, setAllocation] = useState<CapitalAllocationResponse | null>(null);
  const [forecast, setForecast] = useState<AnalyzeOperatingForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allocationRequest = useMemo<CapitalAllocationRequest>(
    () => ({
      portfolio_name: "FY27 software product expansion",
      business_context:
        "A hypothetical mid-market software company is choosing among three growth investments under a shared FY27 capital ceiling. All forecasts are synthetic analyst assumptions, not actual company results.",
      currency: "USD",
      capital_budget: capitalBudget,
      discount_rate_percent: discountRate,
      investments: INVESTMENTS,
      baseline_investment_ids: ["data-foundation", "international-self-serve"],
    }),
    [capitalBudget, discountRate],
  );

  const forecastRequest = useMemo<AnalyzeOperatingForecastRequest>(() => {
    const downside = forecastAssumptions(
      discountRate,
      "Enterprise AI module — downside",
      ["5", "7", "8", "8", "6"],
      "72",
      "61",
      "8",
    );
    const base = forecastAssumptions(
      discountRate,
      "Enterprise AI module — base",
      ["12", "15", "18", "16", "12"],
      "78",
      "58",
      "6",
    );
    const upside = forecastAssumptions(
      discountRate,
      "Enterprise AI module — upside",
      ["17", "21", "23", "19", "15"],
      "81",
      "56",
      "5",
    );
    return {
      base_case: base,
      scenarios: [
        { name: "Downside", probability_percent: "25", assumptions: downside },
        { name: "Base", probability_percent: "50", assumptions: base },
        { name: "Upside", probability_percent: "25", assumptions: upside },
      ],
    };
  }, [discountRate]);

  async function runAnalysis() {
    setLoading(true);
    setError(null);
    try {
      const [allocationResult, forecastResult] = await Promise.all([
        financialModelingApi.optimizeCapitalAllocation(allocationRequest),
        financialModelingApi.analyzeOperatingForecast(forecastRequest),
      ]);
      setAllocation(allocationResult);
      setForecast(forecastResult);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  async function downloadMemo() {
    setError(null);
    try {
      const blob = await financialModelingApi.downloadExecutiveInvestmentMemo({
        allocation: allocationRequest,
        forecast_analysis: forecastRequest,
      });
      triggerBlobDownload(blob, "fy27-software-product-investment-memo.pdf");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Could not generate the memo.");
    }
  }

  const selected = new Set(allocation?.selected_investment_ids ?? []);
  const forecastChart = forecast?.base_case.years.map((year) => ({
    year: `Y${year.year}`,
    revenue: Number(year.revenue),
    ebitda: Number(year.ebitda),
    freeCashFlow: Number(year.free_cash_flow),
  })) ?? [];
  const scenarioChart = forecast?.scenarios.map((scenario) => ({
    name: scenario.name,
    npv: Number(scenario.npv),
  })) ?? [];
  const sensitivityChart = forecast?.sensitivity
    .filter((point) => point.case !== "base")
    .map((point) => ({
      name: `${point.driver.replaceAll("_", " ")} · ${point.case}`,
      npv: Number(point.npv),
    })) ?? [];

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/"
        className="group inline-flex items-center gap-2 text-sm text-muted hover:text-parchment transition-colors w-fit"
      >
        <ArrowLeft size={16} className="transition-transform group-hover:-translate-x-1" />
        Back to overview
      </Link>

      <div>
        <span className="text-[11px] uppercase tracking-wider text-ledger">
          Finance leadership / capital allocation
        </span>
        <h1 className="font-display text-[30px] mt-1">Investment portfolio decision</h1>
        <p className="text-muted text-sm mt-1 max-w-3xl">
          A traceable five-year operating forecast and exact 0-1 capital-budget optimization.
          The worked case is clearly hypothetical and can be rerun with a different budget or
          discount rate.
        </p>
      </div>

      <Panel eyebrow="Decision inputs" title="FY27 software product expansion">
        <div className="grid grid-cols-1 md:grid-cols-[220px_220px_1fr] gap-4 items-end">
          <Field label="Capital budget" hint="Shared ceiling across all investments">
            <TextInput value={capitalBudget} onChange={(event) => setCapitalBudget(event.target.value)} />
          </Field>
          <Field label="Discount rate (%)" hint="Jan 2026 software WACC benchmark: 9.34%">
            <TextInput value={discountRate} onChange={(event) => setDiscountRate(event.target.value)} />
          </Field>
          <div className="flex gap-2 md:justify-end">
            <Button onClick={runAnalysis} disabled={loading}>
              {loading ? "Calculating…" : "Optimize portfolio"}
            </Button>
            <Button variant="ghost" onClick={downloadMemo} disabled={!allocation || loading}>
              <span className="inline-flex items-center gap-2"><Download size={15} /> Executive memo</span>
            </Button>
          </div>
        </div>
        {error && <p className="text-signal-down text-sm mt-4">{error}</p>}
      </Panel>

      {allocation && forecast && (
        <>
          <Panel eyebrow="Recommendation" title="Fund the value-maximizing feasible combination">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
              <Stat label="Capital used" value={formatUsd(allocation.capital_used)} />
              <Stat label="Utilization" value={allocation.capital_utilization_percent} suffix="%" />
              <Stat label="Portfolio NPV" value={formatUsd(allocation.portfolio_npv)} tone="up" />
              <Stat
                label="Portfolio IRR"
                value={allocation.portfolio_irr_percent ?? "n/m"}
                suffix={allocation.portfolio_irr_percent ? "%" : undefined}
              />
              <Stat label="Downside exposure" value={formatUsd(allocation.downside_exposure)} tone="down" />
            </div>
            <p className="text-sm text-muted mt-5">
              Selected: <span className="text-parchment">{allocation.selected_investment_ids.join(", ")}</span>.
              Incremental NPV versus the defined baseline: {formatUsd(allocation.incremental_npv_vs_baseline)}.
            </p>
            <p className="text-xs text-muted mt-2">{allocation.optimization_method}</p>
          </Panel>

          <Panel eyebrow="Investment set" title="Opportunity economics and constraints">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-[11px] uppercase tracking-wider text-muted border-b border-ink-border">
                  <tr>
                    <th className="pb-2">Decision</th><th className="pb-2">Investment</th>
                    <th className="pb-2">Capital</th><th className="pb-2">NPV</th>
                    <th className="pb-2">IRR</th><th className="pb-2">Payback</th>
                    <th className="pb-2">Downside NPV</th><th className="pb-2">Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {allocation.investments.map((investment) => (
                    <tr key={investment.investment_id} className="border-b border-ink-border/60">
                      <td className={selected.has(investment.investment_id) ? "py-3 text-signal-up" : "py-3 text-muted"}>
                        {selected.has(investment.investment_id) ? "Fund" : "Defer"}
                      </td>
                      <td className="py-3 pr-4 text-parchment">{investment.name}</td>
                      <td className="py-3 font-data">{formatUsd(investment.initial_capital)}</td>
                      <td className="py-3 font-data">{formatUsd(investment.npv)}</td>
                      <td className="py-3 font-data">{investment.irr_percent ? `${Number(investment.irr_percent).toFixed(1)}%` : "n/m"}</td>
                      <td className="py-3 font-data">{investment.payback_period ? `${Number(investment.payback_period).toFixed(1)}y` : "Beyond"}</td>
                      <td className="py-3 font-data">{formatUsd(investment.downside_npv)}</td>
                      <td className="py-3 font-data">{investment.strategic_priority}/5</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <Panel eyebrow="Five-year forecast" title="Revenue, EBITDA, and free cash flow">
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={forecastChart}>
                    <CartesianGrid stroke="#26303b" strokeDasharray="3 3" />
                    <XAxis dataKey="year" stroke="#788391" />
                    <YAxis stroke="#788391" tickFormatter={formatCompactUsd} />
                    <Tooltip contentStyle={{ background: "#111820", border: "1px solid #2b3744" }} />
                    <Legend />
                    <Line dataKey="revenue" name="Revenue" stroke="#8ecdc4" strokeWidth={2} />
                    <Line dataKey="ebitda" name="EBITDA" stroke="#d4b46a" strokeWidth={2} />
                    <Line dataKey="freeCashFlow" name="Free cash flow" stroke="#8ab4f8" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="text-xs text-muted mt-3">
                FCFF = EBIT × (1 − tax) + D&amp;A − capex − change in working capital. D&amp;A is
                deducted once in EBIT and added back once as a non-cash expense.
              </p>
            </Panel>

            <Panel eyebrow="Scenario analysis" title="Downside, base, and upside NPV">
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={scenarioChart}>
                    <CartesianGrid stroke="#26303b" strokeDasharray="3 3" />
                    <XAxis dataKey="name" stroke="#788391" />
                    <YAxis stroke="#788391" tickFormatter={formatCompactUsd} />
                    <Tooltip contentStyle={{ background: "#111820", border: "1px solid #2b3744" }} />
                    <Bar dataKey="npv" fill="#4e9f94" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="text-sm text-muted mt-3">
                Probability-weighted expected NPV: <span className="text-parchment font-data">{formatUsd(forecast.probability_weighted_npv)}</span>.
              </p>
            </Panel>
          </div>

          <Panel eyebrow="Driver sensitivity" title="One-way NPV stresses">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sensitivityChart} layout="vertical" margin={{ left: 115 }}>
                  <CartesianGrid stroke="#26303b" strokeDasharray="3 3" />
                  <XAxis type="number" stroke="#788391" tickFormatter={formatCompactUsd} />
                  <YAxis type="category" dataKey="name" stroke="#788391" width={150} tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#111820", border: "1px solid #2b3744" }} />
                  <Bar dataKey="npv" fill="#4e9f94" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-muted mt-3">
              {forecast.sensitivity_range_note} Revenue-growth break-even: {forecast.break_even_revenue_growth_percent ?? "not reached"}%.
            </p>
          </Panel>

          <Panel eyebrow="Financial risk" title="Traceable risk assumptions">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {allocation.investments.map((investment) => (
                <div key={investment.investment_id} className="border border-ink-border rounded-sm p-4">
                  <h3 className="text-parchment text-sm font-medium">{investment.name}</h3>
                  <p className="text-xs text-muted leading-relaxed mt-2">{investment.risk_assumption}</p>
                  <p className="text-xs text-muted mt-3">
                    Dependencies: {investment.dependencies.length ? investment.dependencies.join(", ") : "None"}
                  </p>
                </div>
              ))}
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
