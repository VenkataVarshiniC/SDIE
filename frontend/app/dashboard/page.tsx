"use client";

import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Panel } from "@/components/ui/panel";
import { Stat } from "@/components/ui/stat";
import { Button, Field, TextInput } from "@/components/ui/field";
import { financialModelingApi, ApiError } from "@/lib/api-client";
import type { CashFlowModelResponse, SensitivityResponse } from "@/lib/types";

interface CashFlowRow {
  period: number;
  amount: string;
}

const DEFAULT_ROWS: CashFlowRow[] = [
  { period: 0, amount: "-1000000" },
  { period: 1, amount: "350000" },
  { period: 2, amount: "400000" },
  { period: 3, amount: "450000" },
  { period: 4, amount: "500000" },
];

export default function FinancialModelingPage() {
  const [projectName, setProjectName] = useState("Market expansion — EU");
  const [discountRate, setDiscountRate] = useState("9");
  const [rows, setRows] = useState<CashFlowRow[]>(DEFAULT_ROWS);
  const [result, setResult] = useState<CashFlowModelResponse | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
        cash_flows: rows.map((r) => ({ period: r.period, amount: r.amount })),
      });
      setResult(model);

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

  const tornadoData = sensitivity
    ? [
        { label: "Low (-30%)", value: Number(sensitivity.npv_low) },
        { label: "Base", value: Number(sensitivity.npv_base) },
        { label: "High (+30%)", value: Number(sensitivity.npv_high) },
      ]
    : [];

  return (
    <div className="flex flex-col gap-6">
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
    </div>
  );
}

function formatMoney(value: string, currency: string): string {
  const n = Number(value);
  const sign = n < 0 ? "-" : "";
  return `${sign}${currency} ${Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}
