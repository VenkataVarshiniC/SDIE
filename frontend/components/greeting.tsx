"use client";

import { useEffect, useState } from "react";
import { workspaceApi } from "@/lib/api-client";

function timeOfDayGreeting(hour: number): string {
  if (hour < 5) return "Good evening";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function summarize(statuses: string[]): string {
  if (statuses.length === 0) {
    return "No engagements yet — start one below.";
  }
  const complete = statuses.filter((s) => s === "complete").length;
  const inProgress = statuses.length - complete;

  if (inProgress === 0) {
    return `All ${complete} engagement${complete === 1 ? "" : "s"} complete.`;
  }
  if (complete === 0) {
    return `${inProgress} engagement${inProgress === 1 ? "" : "s"} in progress.`;
  }
  return `${inProgress} engagement${inProgress === 1 ? "" : "s"} in progress, ${complete} complete.`;
}

export function Greeting() {
  const [now, setNow] = useState(() => new Date());
  const [summary, setSummary] = useState<string | null>(null);

  useEffect(() => {
    // Re-checks the clock every minute so the greeting flips from
    // "morning" to "afternoon" etc. while the tab stays open, rather than
    // only on the initial mount. A minute is frequent enough to feel live
    // without running a visible per-second clock on a dashboard.
    const interval = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    workspaceApi
      .listEngagements()
      .then((engagements) => setSummary(summarize(engagements.map((e) => e.status))))
      .catch(() => {
        // status summary is a nice-to-have; a failed fetch here shouldn't
        // block or clutter the homepage with an error banner
        setSummary(null);
      });
  }, []);

  const dateLabel = now.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="mb-4">
      <p className="text-muted text-[11px] uppercase tracking-wider">{dateLabel}</p>
      <p className="font-display text-[19px] text-parchment mt-1">
        {timeOfDayGreeting(now.getHours())}
        {summary && (
          <>
            {" — "}
            <span className="text-ledger">{summary}</span>
          </>
        )}
      </p>
    </div>
  );
}
