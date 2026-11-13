"use client";

import { useMemo, useState } from "react";

import { AGENT_LABELS, SEVERITY_DOTS, SEVERITY_LABELS } from "@/lib/labels";
import type { Finding } from "@/lib/types";

const SEVERITIES = ["all", "critical", "high", "medium", "low", "info"] as const;

export default function FindingsTable({ findings }: { findings: Finding[] }) {
  const [severity, setSeverity] = useState<typeof SEVERITIES[number]>("all");
  const [agent, setAgent] = useState("all");
  const [query, setQuery] = useState("");

  const agents = useMemo(
    () => Array.from(new Set(findings.map((finding) => finding.agent))).sort(),
    [findings]
  );

  const filtered = useMemo(
    () =>
      findings.filter((finding) => {
        if (severity !== "all" && finding.severity !== severity) return false;
        if (agent !== "all" && finding.agent !== agent) return false;
        if (query.trim()) {
          const haystack = `${finding.title} ${finding.description} ${finding.url} ${finding.category}`.toLowerCase();
          if (!haystack.includes(query.trim().toLowerCase())) return false;
        }
        return true;
      }),
    [findings, severity, agent, query]
  );

  const counts = useMemo(() => {
    const result: Record<string, number> = { all: findings.length };
    for (const finding of findings) {
      result[finding.severity] = (result[finding.severity] ?? 0) + 1;
    }
    return result;
  }, [findings]);

  return (
    <section className="card overflow-hidden" aria-label="Problèmes détectés">
      <header className="border-b border-surface-800 px-4 py-3.5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-heading-sm font-semibold text-surface-50">Problèmes détectés</h2>
          <p className="numeric text-body-xs text-surface-500">
            {filtered.length}/{findings.length} affichés
          </p>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <div className="relative min-w-0 flex-1 sm:max-w-xs">
            <svg className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-surface-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher une règle, une URL…"
              className="input h-8 w-full pl-8 pr-8 text-body-xs"
              aria-label="Rechercher dans les problèmes"
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-surface-500 hover:text-surface-200"
                aria-label="Effacer la recherche"
              >
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as typeof SEVERITIES[number])}
            className="input h-8 w-auto appearance-none py-0 pr-7 text-body-xs"
            aria-label="Filtrer par sévérité"
          >
            {SEVERITIES.map((value) => (
              <option key={value} value={value}>
                {value === "all" ? "Toutes sévérités" : SEVERITY_LABELS[value]} ({counts[value] ?? 0})
              </option>
            ))}
          </select>

          <select
            value={agent}
            onChange={(e) => setAgent(e.target.value)}
            className="input h-8 w-auto appearance-none py-0 pr-7 text-body-xs"
            aria-label="Filtrer par agent"
          >
            <option value="all">Tous les agents</option>
            {agents.map((value) => (
              <option key={value} value={value}>
                {AGENT_LABELS[value] ?? value}
              </option>
            ))}
          </select>
        </div>
      </header>

      {filtered.length === 0 ? (
        <div className="px-6 py-12 text-center">
          <p className="text-body-sm font-medium text-surface-200">Aucun problème affiché</p>
          <p className="mt-1 text-body-xs text-surface-500">
            {findings.length === 0 ? "Ce scan n'a relevé aucun problème." : "Aucun résultat ne correspond aux filtres."}
          </p>
        </div>
      ) : (
        <div className="divide-y divide-surface-800/80">
          {filtered.map((finding) => (
            <details key={finding.id} className="group px-4 py-2.5 transition-colors open:bg-surface-925/60 hover:bg-surface-850/40">
              <summary className="flex cursor-pointer list-none items-center gap-3">
                <span
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${SEVERITY_DOTS[finding.severity] ?? SEVERITY_DOTS.info}`}
                  aria-hidden="true"
                />
                <span className="w-14 shrink-0 text-[11px] font-medium uppercase tracking-[0.08em] text-surface-400">
                  {SEVERITY_LABELS[finding.severity] ?? finding.severity}
                </span>
                <span className="min-w-0 flex-1 truncate text-body-sm text-surface-100">{finding.title}</span>
                <span className="hidden shrink-0 font-mono text-[10px] uppercase tracking-wider text-surface-500 sm:inline">
                  {AGENT_LABELS[finding.agent] ?? finding.agent}
                </span>
                <svg className="h-3.5 w-3.5 shrink-0 text-surface-600 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </summary>

              <div className="mt-3 space-y-2.5 border-l border-surface-800 py-1 pl-4 ml-0.5">
                {finding.description && (
                  <p className="text-body-sm leading-relaxed text-surface-400">{finding.description}</p>
                )}

                {finding.url && (
                  <a
                    href={finding.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-1.5 font-mono text-[11px] text-surface-500 transition-colors hover:text-brand-300"
                  >
                    <svg className="mt-0.5 h-3 w-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                    <span className="break-all">{finding.url}</span>
                  </a>
                )}

                {finding.evidence && (
                  <div className="rounded border border-surface-800 bg-surface-950">
                    <div className="flex items-center justify-between border-b border-surface-800 px-2.5 py-1.5">
                      <span className="eyebrow">Preuve</span>
                      <button
                        onClick={() => navigator.clipboard.writeText(finding.evidence!)}
                        className="rounded px-1 text-[11px] text-surface-500 transition-colors hover:text-surface-200"
                        aria-label="Copier la preuve"
                      >
                        Copier
                      </button>
                    </div>
                    <pre className="max-h-44 overflow-auto whitespace-pre-wrap break-words px-2.5 py-2 font-mono text-[11px] leading-relaxed text-surface-400">
                      {finding.evidence}
                    </pre>
                  </div>
                )}

                {finding.remediation && (
                  <div className="border-l-2 border-brand-500/50 pl-3">
                    <p className="eyebrow text-brand-400">Remédiation</p>
                    <p className="mt-1 text-body-sm leading-relaxed text-surface-300">{finding.remediation}</p>
                  </div>
                )}

                {finding.category && (
                  <span className="badge-neutral">{finding.category}</span>
                )}
              </div>
            </details>
          ))}
        </div>
      )}
    </section>
  );
}
