"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import AgentStatusGrid, { type AgentState } from "@/components/AgentStatusGrid";
import FindingsTable from "@/components/FindingsTable";
import ScanProgress from "@/components/ScanProgress";
import ScoreGauge from "@/components/ScoreGauge";
import {
  ApiError,
  downloadReport,
  formatDate,
  scansApi,
  sitesApi,
} from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { STATUS_DOTS, STATUS_LABELS, scoreGrade } from "@/lib/labels";
import type { ScanDetail, ServerEvent } from "@/lib/types";

const BASE_AGENTS = ["reliability", "security"];

export default function ScanPage() {
  const params = useParams<{ id: string }>();
  const scanId = Array.isArray(params.id) ? params.id[0] : params.id;
  const { user, loading } = useRequireAuth();
  const router = useRouter();

  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [live, setLive] = useState<Record<string, AgentState>>({});
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [retesting, setRetesting] = useState(false);

  const load = useCallback(async () => {
    if (!scanId) return;
    setRefreshing(true);
    try {
      setScan(await scansApi.get(scanId));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    } finally {
      setRefreshing(false);
    }
  }, [scanId]);

  useEffect(() => {
    if (user && scanId) load();
  }, [user, scanId, load]);

  const handleEvent = useCallback((event: ServerEvent) => {
    if (event.type === "agent_start") {
      const agent = String(event.agent);
      setLive((previous) => ({
        ...previous,
        [agent]: {
          agent,
          label: typeof event.label === "string" ? event.label : undefined,
          status: "running",
          findings: 0,
        },
      }));
    }
    if (event.type === "agent_done") {
      const agent = String(event.agent);
      setLive((previous) => ({
        ...previous,
        [agent]: {
          agent,
          label: typeof event.label === "string" ? event.label : undefined,
          status: String(event.status ?? "completed"),
          score: event.score === null || event.score === undefined ? null : Number(event.score),
          findings: Number(event.findings ?? 0),
          duration_ms: Number(event.duration_ms ?? 0),
        },
      }));
    }
  }, []);

  const handleDone = useCallback(() => {
    load();
  }, [load]);

  const expectedAgents = useMemo(() => {
    if (!scan) return [];
    if (scan.mode === "quick") return BASE_AGENTS;
    const names = [...BASE_AGENTS, "performance", "accessibility"];
    if (scan.scenario) names.push("functional");
    return names;
  }, [scan]);

  const agents: AgentState[] = useMemo(() => {
    return expectedAgents.map((name) => {
      if (live[name]) return live[name];
      const finished = scan?.agent_results.find((result) => result.agent === name);
      if (finished) {
        const count = scan?.findings.filter((finding) => finding.agent === name).length ?? 0;
        return {
          agent: name,
          status: finished.status,
          score: finished.score,
          findings: count,
          duration_ms: finished.duration_ms,
          error: finished.error,
        };
      }
      return { agent: name, status: "pending" };
    });
  }, [expectedAgents, live, scan]);

  const exportReport = async (format: "json" | "html" | "pdf") => {
    if (!scanId) return;
    setExporting(format);
    try {
      await downloadReport(scanId, format);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export impossible.");
    } finally {
      setExporting(null);
    }
  };

  const retest = async (mode: "quick" | "full" = scan?.mode ?? "quick") => {
    if (!scan) return;
    setRetesting(true);
    setError(null);
    try {
      const created = await sitesApi.launchScan(
        scan.site_id,
        mode,
        scan.scenario ?? undefined,
      );
      router.push(`/scans/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Relance du scan impossible.");
      setRetesting(false);
    }
  };

  if (loading || !user) {
    return (
      <main className="container-app flex min-h-[60vh] items-center justify-center py-16">
        <div className="flex items-center gap-3 text-body-sm text-surface-500">
          <span
            className="h-3.5 w-3.5 animate-spin rounded-full border border-surface-700 border-t-brand-400"
            aria-hidden="true"
          />
          Chargement du scan…
        </div>
      </main>
    );
  }

  if (!scan) {
    return (
      <main className="container-app flex min-h-[60vh] items-center justify-center py-16">
        <div className="text-center">
          <div className="empty-state-icon">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h1 className="text-heading-md font-semibold text-surface-50">Scan introuvable</h1>
          <p className="mt-1.5 text-body-sm text-surface-500">{error ?? "Chargement du scan…"}</p>
          <Link href="/scans" className="btn-secondary btn-sm mt-5">
            Retour à l&apos;historique
          </Link>
        </div>
      </main>
    );
  }

  const active = scan.status === "queued" || scan.status === "running";

  return (
    <main className="container-app space-y-7 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={`/sites/${scan.site_id}`}
          className="btn-ghost btn-sm -ml-2 max-w-full gap-1.5"
        >
          <svg className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="truncate">{scan.site_name || scan.site_url}</span>
        </Link>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => retest()}
            disabled={retesting || active}
            title={active ? "Un scan est déjà en cours pour ce site" : "Relancer un scan avec les mêmes paramètres"}
            aria-label={`Relancer un scan ${scan.mode === "quick" ? "rapide" : "complet"} sur ${scan.site_url}`}
            className="btn-primary btn-sm"
          >
            <svg
              className={`h-3.5 w-3.5 ${retesting ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Retester
          </button>
          <button
            type="button"
            onClick={load}
            disabled={refreshing}
            aria-label="Actualiser les données du scan"
            className="btn-secondary btn-sm"
          >
            <svg className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Actualiser
          </button>
        </div>
      </div>

      <header className="card overflow-hidden">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-surface-800 px-5 py-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="truncate font-mono text-heading-md font-medium text-surface-50">
                {scan.id}
              </h1>
              <span className="badge badge-neutral shrink-0">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${STATUS_DOTS[scan.status] ?? STATUS_DOTS.queued} ${
                    active ? "animate-pulse" : ""
                  }`}
                  aria-hidden="true"
                />
                {STATUS_LABELS[scan.status] ?? scan.status}
              </span>
            </div>
            <p className="mt-1 text-body-xs text-surface-500">
              <span className="font-mono">{scan.site_url}</span>
              <span className="mx-1.5 text-surface-700">/</span>
              mode {scan.mode === "quick" ? "rapide" : "complet"}
              <span className="mx-1.5 text-surface-700">/</span>
              {scan.triggered_by}
              <span className="mx-1.5 text-surface-700">/</span>
              {formatDate(scan.created_at)}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-1.5" role="group" aria-label="Exporter le rapport">
            {(["json", "html", "pdf"] as const).map((format) => (
              <button
                key={format}
                onClick={() => exportReport(format)}
                disabled={exporting !== null || active}
                className="btn-secondary btn-sm font-mono uppercase tracking-wider"
                aria-label={`Exporter le rapport en ${format.toUpperCase()}`}
              >
                {exporting === format ? (
                  <svg className="h-3.5 w-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                ) : (
                  format
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-6 px-5 py-6 sm:grid-cols-5">
          <div className="flex flex-col items-center justify-center gap-2 sm:col-span-2 sm:items-start">
            <ScoreGauge score={scan.global_score} size={124} label="Score global" />
            <p className="text-body-xs text-surface-500">
              Note{" "}
              <span className="font-mono font-medium text-surface-200">
                {scan.global_score === null || scan.global_score === undefined
                  ? "—"
                  : scoreGrade(scan.global_score)}
              </span>{" "}
              sur 100
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:col-span-3">
            {(
              [
                ["Fiabilité", scan.reliability_score] as const,
                ["Sécurité", scan.security_score] as const,
                ["Performance", scan.performance_score] as const,
                ["Accessibilité", scan.accessibility_score] as const,
              ] as const
            ).map(([label, value]) => (
              <div
                key={label}
                className="flex items-center justify-center rounded-md border border-surface-800 bg-surface-925 py-4"
              >
                <ScoreGauge score={value ?? null} size={68} label={label} />
              </div>
            ))}
          </div>
        </div>

        {scan.mode === "quick" && (
          <div className="flex flex-col gap-3 border-t border-surface-800 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-2xl text-body-xs leading-relaxed text-surface-400">
              <span className="font-medium text-surface-200">
                Performance et accessibilité non mesurées.
              </span>{" "}
              Un scan rapide ne lance que deux agents (fiabilité, sécurité). Les deux autres
              dimensions nécessitent un scan complet avec navigateur.
            </p>
            <button
              type="button"
              onClick={() => retest("full")}
              disabled={retesting || active}
              aria-label={`Relancer un scan complet (4 agents) sur ${scan.site_url}`}
              className="btn-secondary btn-sm shrink-0 self-start sm:self-auto"
            >
              <svg
                className={`h-3.5 w-3.5 ${retesting ? "animate-spin" : ""}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Relancer en complet
            </button>
          </div>
        )}
      </header>

      <div aria-live="polite">
        {(scan.error || error) && (
          <div
            className="card flex items-start gap-2.5 border-danger-500/30 bg-danger-500/5 px-4 py-3 animate-fade-in"
            role="alert"
          >
            <svg className="mt-0.5 h-4 w-4 shrink-0 text-danger-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-body-sm text-danger-300">{scan.error ?? error}</p>
          </div>
        )}
      </div>

      <section className="space-y-3" aria-label="Agents d'analyse">
        <header className="section-header mb-0">
          <div>
            <h2 className="section-title">Agents d&apos;analyse</h2>
            <p className="section-subtitle">
              {agents.filter((agent) => agent.status === "completed").length}/{agents.length} terminés
            </p>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-surface-500">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-info-400" aria-hidden="true" />
              En cours
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-400" aria-hidden="true" />
              Terminé
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-surface-600" aria-hidden="true" />
              En attente
            </span>
          </div>
        </header>
        <AgentStatusGrid agents={agents} />
      </section>

      {active && (
        <section className="card overflow-hidden" aria-label="Progression du scan">
          <header className="panel-header">
            <h2 className="text-heading-sm font-semibold text-surface-50">Journal d&apos;exécution</h2>
            <span className="inline-flex items-center gap-1.5 text-[11px] text-info-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-info-400" aria-hidden="true" />
              diffusion en direct
            </span>
          </header>
          <div className="p-4">
            <ScanProgress scanId={scan.id} onEvent={handleEvent} onDone={handleDone} />
          </div>
        </section>
      )}

      {scan.summary && (
        <section className="card" aria-label="Synthèse">
          <header className="panel-header">
            <h2 className="text-heading-sm font-semibold text-surface-50">Synthèse</h2>
            <span className="eyebrow">Générée par l&apos;analyste</span>
          </header>
          <div className="px-5 py-4">
            <p className="whitespace-pre-wrap text-body-sm leading-relaxed text-surface-300">
              {scan.summary}
            </p>
          </div>
        </section>
      )}

      <FindingsTable findings={scan.findings} />
    </main>
  );
}
