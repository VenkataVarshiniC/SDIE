import Link from "next/link";
import { Panel } from "@/components/ui/panel";

const WORKSPACE_MODULE = {
  href: "/dashboard/workspace",
  eyebrow: "00 — Orchestration",
  title: "Workspace",
  description:
    "The front door: walk a case from problem framing through evidence, quant analysis, and synthesis to a delivered recommendation. Start here.",
};

const MODULES = [
  {
    href: "/dashboard",
    eyebrow: "01 — Quant core",
    title: "Financial modeling",
    description:
      "Discounted cash flow, scenario weighting, one-way sensitivity, industry-benchmarked assumption flags. Deterministic, reproducible, no model in the loop.",
  },
  {
    href: "/dashboard/decision-analysis",
    eyebrow: "02 — Quant core",
    title: "Decision analysis",
    description:
      "Multi-criteria ranking, decision trees, Monte Carlo, and weight-robustness checks. Every score traces to a stated weight and a raw input.",
  },
  {
    href: "/dashboard/evidence-research",
    eyebrow: "03 — Evidence core",
    title: "Evidence research",
    description:
      "Ingest source documents, retrieve by exact-excerpt citation via Postgres full-text search. No paraphrasing, no vector database.",
  },
  {
    href: "/dashboard/recommendation-synthesis",
    eyebrow: "04 — Synthesis core",
    title: "Recommendation synthesis",
    description:
      "Fuses quant output with cited evidence into one auditable recommendation, with append-only overrides and a board-ready PDF export.",
  },
  {
    href: "/dashboard/problem-framing",
    eyebrow: "05 — Framing core",
    title: "Problem framing",
    description:
      "Guided strategy frameworks — Five Forces, SWOT — as structured section lists, so a user can't skip a dimension of the analysis.",
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-col gap-10">
      <div className="border-b border-ink-border pb-8">
        <p className="text-ledger text-[11px] uppercase tracking-wider mb-3">
          Structured decision support — not a chat interface
        </p>
        <h1 className="font-display text-[34px] leading-tight max-w-2xl text-parchment">
          Every recommendation on this platform traces back to a number, a weight, or a cited
          source.
        </h1>
        <p className="text-muted mt-3 max-w-xl text-sm leading-relaxed">
          Six engines are live: financial modeling, decision science, evidence-grounded
          retrieval, guided strategy frameworks, and an evidence-to-recommendation synthesis
          layer — orchestrated end to end by the workspace below. Validated against a real
          historical decision in{" "}
          <code className="text-ledger text-xs">case-studies</code>.
        </p>
      </div>

      <Link href={WORKSPACE_MODULE.href} className="group">
        <Panel className="transition-colors group-hover:border-ledger bg-ink-2">
          <span className="text-[11px] uppercase tracking-wider text-ledger">
            {WORKSPACE_MODULE.eyebrow}
          </span>
          <h2 className="font-display text-[26px] text-parchment mt-2 mb-2">
            {WORKSPACE_MODULE.title}
          </h2>
          <p className="text-sm text-muted leading-relaxed max-w-2xl">
            {WORKSPACE_MODULE.description}
          </p>
        </Panel>
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {MODULES.map((mod) => (
          <Link key={mod.href} href={mod.href} className="group">
            <Panel className="h-full transition-colors group-hover:border-ledger">
              <span className="text-[11px] uppercase tracking-wider text-ledger">{mod.eyebrow}</span>
              <h2 className="font-display text-[22px] text-parchment mt-2 mb-2">{mod.title}</h2>
              <p className="text-sm text-muted leading-relaxed">{mod.description}</p>
            </Panel>
          </Link>
        ))}
      </div>
    </div>
  );
}
