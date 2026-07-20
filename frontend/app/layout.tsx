import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "SDIE — Strategic Decision Intelligence Engine",
  description: "Structured strategic decision support for executives.",
};

const NAV = [
  { href: "/dashboard", label: "Financial modeling" },
  { href: "/dashboard/decision-analysis", label: "Decision analysis" },
  { href: "/dashboard/evidence-research", label: "Evidence research"},
  { href: "/dashboard/recommendation-synthesis", label: "Recommendation synthesis"},
  { href: "/dashboard/problem-framing", label: "Problem framing"}
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-body bg-ink-0 text-parchment">
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-ink-border px-8 py-5 flex items-baseline justify-between">
            <div className="flex items-baseline gap-3">
              <span className="font-display text-[22px] tracking-tight"><a></a>SDIE</span>
              <span className="text-muted text-sm">Strategic Decision Intelligence Engine</span>
            </div>
            <nav className="flex gap-6 text-sm">
              {NAV.map((item) => (
                <Link key={item.href} href={item.href} className="text-muted hover:text-parchment transition-colors">
                  {item.label}
                </Link>
              ))}
            </nav>
          </header>
          <main className="flex-1 px-8 py-10 max-w-6xl w-full mx-auto">{children}</main>
          <footer className="border-t border-ink-border px-8 py-4 text-xs text-muted">
            Every figure on this screen traces to a model run — click a value to see its inputs.
          </footer>
        </div>
      </body>
    </html>
  );
}
