"use client";

import type { Layer, RunReport, StepResult } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const LAYER_BADGE: Record<Layer, { label: string; cls: string }> = {
  ui: { label: "UI", cls: "border-accent-500/40 bg-accent-500/10 text-accent-300" },
  api: { label: "API", cls: "border-info-500/40 bg-info-500/10 text-info-300" },
  db: { label: "DB", cls: "border-brand-500/35 bg-brand-500/10 text-brand-300" },
};

const LAYER_TITLE: Record<Layer, string> = {
  ui: "text-accent-300",
  api: "text-info-300",
  db: "text-brand-300",
};

function AnomalyBadges({ step }: { step: StepResult }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {step.anomalies.map((a, i) => {
        const badge = LAYER_BADGE[a.layer];
        return (
          <span key={i} className={`badge ${badge.cls}`} title={a.message}>
            {badge.label}
          </span>
        );
      })}
    </div>
  );
}

function StepCard({ step }: { step: StepResult }) {
  const failed = step.anomalies.length > 0;

  return (
    <details className="card group">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded border font-mono text-[11px] font-medium ${
              failed
                ? "border-danger-500/40 bg-danger-500/10 text-danger-300"
                : "border-brand-500/35 bg-brand-500/10 text-brand-300"
            }`}
          >
            {step.index}
          </span>
          <span className="truncate text-body-sm font-medium text-surface-100">{step.title}</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <AnomalyBadges step={step} />
          <svg className="h-3.5 w-3.5 text-surface-600 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </summary>

      <div className="space-y-4 border-t border-surface-800 px-4 py-4 animate-fade-in">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {(["ui", "api", "db"] as Layer[]).map((layer) => (
            <div key={layer} className="rounded-md border border-surface-800 bg-surface-925 p-3">
              <h4 className={`mb-2.5 text-[11px] font-medium uppercase tracking-[0.12em] ${LAYER_TITLE[layer]}`}>
                {LAYER_BADGE[layer].label}
              </h4>

              {layer === "ui" && (
                <>
                  <p className="break-all font-mono text-[11px] leading-relaxed text-surface-400">
                    {step.ui.action} {step.ui.selector}
                    {step.ui.value ? ` « ${step.ui.value} »` : ""}
                  </p>
                  {step.ui.error && (
                    <p className="mt-2 break-words text-[11px] text-danger-300">{step.ui.error}</p>
                  )}
                  {step.ui.screenshot && (
                    <a
                      href={`${API_URL}/reports/${step.ui.screenshot.split("/").slice(-2).join("/")}`}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2.5 inline-flex items-center gap-1.5 text-[11px] text-brand-300 transition-colors hover:text-brand-200"
                    >
                      Capture d&apos;écran
                      <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </a>
                  )}
                </>
              )}

              {layer === "api" &&
                (step.api.length === 0 ? (
                  <p className="text-[11px] text-surface-500">Aucun échange capturé</p>
                ) : (
                  <ul className="max-h-40 space-y-1 overflow-y-auto font-mono text-[10px]">
                    {step.api.slice(-10).map((o, i) => (
                      <li key={i} className="flex items-center gap-1.5">
                        <span
                          className={`rounded px-1 py-0.5 font-medium ${
                            o.status >= 400
                              ? "bg-danger-500/10 text-danger-300"
                              : "bg-brand-500/10 text-brand-300"
                          }`}
                        >
                          {o.status}
                        </span>
                        <span className="rounded bg-surface-850 px-1 py-0.5 uppercase text-surface-400">
                          {o.method}
                        </span>
                        <span className="min-w-0 flex-1 truncate text-surface-500">{o.url}</span>
                      </li>
                    ))}
                  </ul>
                ))}

              {layer === "db" &&
                (step.db ? (
                  <>
                    <p className="mb-2 break-all font-mono text-[10px] leading-relaxed text-surface-400">
                      {step.db.query}
                    </p>
                    <p className={`text-[11px] font-medium ${step.db.ok ? "text-brand-300" : "text-danger-300"}`}>
                      {step.db.ok ? `${step.db.row_count} ligne(s)` : step.db.error}
                    </p>
                  </>
                ) : (
                  <p className="text-[11px] text-surface-500">Non appliqué</p>
                ))}
            </div>
          ))}
        </div>

        {step.root_cause && (
          <div className="rounded-md border border-warning-500/30 bg-warning-500/[0.05] p-3">
            <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-warning-300">Cause racine</p>
            <p className="mt-1 text-body-xs leading-relaxed text-surface-300">{step.root_cause}</p>
          </div>
        )}
      </div>
    </details>
  );
}

export default function ReportViewer({ report }: { report: RunReport }) {
  const anomaliesByLayer = report.anomalies.reduce(
    (acc, a) => {
      acc[a.layer] = (acc[a.layer] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <section className="card overflow-hidden" aria-label="Rapport tri-couche">
      <header className="panel-header">
        <div>
          <h2 className="text-heading-sm font-semibold text-surface-50">Rapport tri-couche</h2>
          <p className="mt-0.5 font-mono text-[11px] text-surface-500">
            {report.run_id} · {report.steps.length} étape(s)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {(["ui", "api", "db"] as Layer[]).map((layer) => (
            <span key={layer} className={`badge ${LAYER_BADGE[layer].cls}`}>
              {LAYER_BADGE[layer].label} {anomaliesByLayer[layer] ?? 0}
            </span>
          ))}
          <span className={`badge ${report.success ? "badge-success" : "badge-danger"}`}>
            {report.success ? "succès" : "échec"}
          </span>
        </div>
      </header>

      <div className="space-y-4 p-4">
        {report.root_cause && (
          <div className="rounded-md border border-danger-500/30 bg-danger-500/[0.05] p-3" role="alert">
            <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-danger-300">Cause racine globale</p>
            <p className="mt-1 text-body-xs leading-relaxed text-surface-300">{report.root_cause}</p>
          </div>
        )}

        {report.summary && (
          <p className="text-body-sm leading-relaxed text-surface-400">{report.summary}</p>
        )}

        <div className="space-y-2">
          {report.steps.map((step) => (
            <StepCard key={step.index} step={step} />
          ))}
        </div>
      </div>
    </section>
  );
}
