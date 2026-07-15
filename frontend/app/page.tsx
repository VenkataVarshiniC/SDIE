import Link from "next/link";
import { Panel } from "@/components/ui/panel";

const MODULES = [
  {
    href: "/dashboard",
    eyebrow: "01 — Quant core",
    title: "Financial modeling",
    description:
      "Discounted cash flow, scenario weighting, one-way sensitivity. Deterministic, reproducible, no model in the loop.",
  },
  {
    href: "/dashboard/decision-analysis",
    eyebrow: "02 — Quant core",
    title: "Decision analysis",
    description:
      "Multi-criteria ranking and expected-value decision trees. Every score traces to a stated weight and a raw input.",
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
          Two engines are live: the deterministic quant core below. Evidence-grounded synthesis
          and market intelligence are built on top of this foundation next.
        </p>
      </div>

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
