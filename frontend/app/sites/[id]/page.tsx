"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import ScoreGauge from "@/components/ScoreGauge";
import TrendChart from "@/components/TrendChart";
import {
  ApiError,
  formatDate,
  sitesApi,
  timeAgo,
} from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { STATUS_DOTS, STATUS_LABELS, scoreColor } from "@/lib/labels";
import type { HistoryPoint, Schedule, Site } from "@/lib/types";

const SCORE_FIELDS = [
  ["Fiabilité", "reliability_score"],
  ["Sécurité", "security_score"],
  ["Performance", "performance_score"],
  ["Accessibilité", "accessibility_score"],
] as const;

export default function SitePage() {
  const params = useParams<{ id: string }>();
  const siteId = Array.isArray(params.id) ? params.id[0] : params.id;
  const { user, loading } = useRequireAuth();
  const router = useRouter();

  const [site, setSite] = useState<Site | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [cron, setCron] = useState("0 3 * * *");
  const [scheduleMode, setScheduleMode] = useState<"quick" | "full">("quick");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!siteId) return;
    try {
      const [siteData, historyData, scheduleData] = await Promise.all([
        sitesApi.get(siteId),
        sitesApi.history(siteId),
        sitesApi.schedules(siteId),
      ]);
      setSite(siteData);
      setHistory(historyData);
      setSchedules(scheduleData);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, [siteId]);

  useEffect(() => {
    if (user && siteId) load();
  }, [user, siteId, load]);

  const launch = async (mode: "quick" | "full") => {
    if (!siteId) return;
    setBusy(true);
    setError(null);
    try {
      const scan = await sitesApi.launchScan(siteId, mode);
      router.push(`/scans/${scan.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lancement impossible.");
      setBusy(false);
    }
  };

  const saveSchedule = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!siteId) return;
    setBusy(true);
    setError(null);
    try {
      await sitesApi.upsertSchedule(siteId, cron.trim(), scheduleMode);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Planification impossible.");
    } finally {
      setBusy(false);
    }
  };

  const removeSite = async () => {
    if (!siteId) return;
    if (!window.confirm("Supprimer ce site et tous ses scans ?")) return;
    try {
      await sitesApi.remove(Number(siteId));
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Suppression impossible.");
    }
  };

  if (loading || !user || !site) {
    return (
      <main className="container-app flex min-h-[60vh] items-center justify-center py-16">
        <div className="flex items-center gap-3 text-body-sm text-surface-500">
          <span
            className="h-3.5 w-3.5 animate-spin rounded-full border border-surface-700 border-t-brand-400"
            aria-hidden="true"
          />
          {error ?? "Chargement du site…"}
        </div>
      </main>
    );
  }

  const last = site.last_scan;
  const status = last?.status ?? "queued";

  return (
    <main className="container-app space-y-7 py-8">
      <Link href="/" className="btn-ghost btn-sm -ml-2 gap-1.5">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Tableau de bord
      </Link>

      <header className="card overflow-hidden">
        <div className="flex flex-wrap items-start gap-6 px-5 py-6">
          <ScoreGauge score={last?.global_score} size={104} label="Score global" />

          <div className="min-w-0 flex-1">
            <h1 className="truncate text-heading-lg font-semibold text-surface-50">
              {site.name || site.url}
            </h1>
            <a
              href={site.url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-flex max-w-full items-center gap-1.5 truncate font-mono text-body-xs text-surface-500 transition-colors hover:text-brand-300"
            >
              <svg className="h-3 w-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              {site.url}
            </a>

            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-surface-500">
              {last ? (
                <>
                  <span className="inline-flex items-center gap-1.5">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${STATUS_DOTS[status] ?? STATUS_DOTS.queued} ${
                        status === "running" ? "animate-pulse" : ""
                      }`}
                      aria-hidden="true"
                    />
                    {STATUS_LABELS[status] ?? status}
                  </span>
                  <span className="numeric">{last.findings_count} problèmes</span>
                  {last.critical_count > 0 && (
                    <span className="numeric text-danger-300">{last.critical_count} critiques</span>
                  )}
                  <span>{timeAgo(last.created_at)}</span>
                </>
              ) : (
                <span className="italic text-surface-500">Aucun scan effectué</span>
              )}
              <span className="numeric border-l border-surface-800 pl-4">{site.scans_count} scan(s) au total</span>
            </div>
          </div>

          <div className="flex shrink-0 flex-col gap-2 sm:flex-row" role="group" aria-label="Lancer un scan">
            <button
              type="button"
              onClick={() => launch("quick")}
              disabled={busy}
              aria-label="Lancer un scan rapide : 2 agents, fiabilité et sécurité"
              className="group flex flex-col items-start gap-0.5 rounded-md border border-surface-800 bg-surface-925 px-4 py-2.5 text-left transition-colors hover:border-surface-700 hover:bg-surface-900 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <span className="flex items-center gap-2 text-body-sm font-medium text-surface-100">
                <svg className="h-3.5 w-3.5 text-surface-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Scan rapide
              </span>
              <span className="pl-[22px] text-[11px] text-surface-500">2 agents · fiabilité + sécurité</span>
            </button>

            <button
              type="button"
              onClick={() => launch("full")}
              disabled={busy}
              aria-label="Lancer un scan complet : 4 agents, fiabilité, sécurité, performance et accessibilité"
              className="group flex flex-col items-start gap-0.5 rounded-md border border-brand-500/35 bg-brand-500/10 px-4 py-2.5 text-left transition-colors hover:border-brand-400/60 hover:bg-brand-500/15 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <span className="flex items-center gap-2 text-body-sm font-medium text-brand-300">
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                </svg>
                Scan complet
                <span className="badge badge-primary ml-0.5">Recommandé</span>
              </span>
              <span className="pl-[22px] text-[11px] text-brand-300/70">4 agents · + performance & accessibilité</span>
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="card flex items-start gap-2.5 border-danger-500/30 bg-danger-500/5 px-4 py-3" role="alert">
          <svg className="mt-0.5 h-4 w-4 shrink-0 text-danger-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-body-sm text-danger-300">{error}</p>
        </div>
      )}

      <TrendChart points={history} />

      <section className="grid gap-5 lg:grid-cols-[2fr_1fr]" aria-label="Historique et planification">
        <div className="card overflow-hidden">
          <header className="panel-header">
            <h2 className="text-heading-sm font-semibold text-surface-50">Historique des scans</h2>
            <span className="numeric text-body-xs text-surface-500">{history.length} entrée(s)</span>
          </header>

          {history.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <div className="empty-state-icon">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <h3 className="empty-state-title">Aucun scan terminé</h3>
              <p className="empty-state-description">Lancez-en un pour voir apparaître les résultats.</p>
            </div>
          ) : (
            <div className="max-h-[420px] divide-y divide-surface-800/80 overflow-y-auto">
              {[...history].reverse().map((point) => (
                <Link
                  key={point.scan_id}
                  href={`/scans/${point.scan_id}`}
                  className="group flex items-center gap-4 px-4 py-3 transition-colors hover:bg-surface-850/50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-mono text-body-xs text-surface-200">{point.scan_id}</p>
                    <p className="mt-0.5 text-[11px] text-surface-500">{formatDate(point.created_at)}</p>
                  </div>

                  <div className="hidden items-center gap-3 sm:flex">
                    {SCORE_FIELDS.map(([label, field]) => {
                      const value = point[field];
                      return (
                        <span key={field} className="flex flex-col items-end leading-tight">
                          <span className="numeric text-body-xs" style={{ color: scoreColor(value) }}>
                            {value === null || value === undefined ? "—" : Math.round(value)}
                          </span>
                          <span className="text-[10px] uppercase tracking-[0.08em] text-surface-600">
                            {label.slice(0, 4)}
                          </span>
                        </span>
                      );
                    })}
                  </div>

                  <div className="w-10 shrink-0 text-right">
                    <span
                      className="numeric text-body-md font-medium"
                      style={{ color: scoreColor(point.global_score) }}
                    >
                      {point.global_score === null || point.global_score === undefined
                        ? "—"
                        : Math.round(point.global_score)}
                    </span>
                  </div>
                  <svg className="h-3.5 w-3.5 shrink-0 text-surface-700 transition-colors group-hover:text-surface-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-5">
          <form onSubmit={saveSchedule} className="card" aria-label="Planification de scan">
            <header className="panel-header">
              <h2 className="text-heading-sm font-semibold text-surface-50">Scan planifié</h2>
              <span className="badge badge-neutral font-mono">cron</span>
            </header>

            <div className="space-y-4 p-5">
              <div>
                <label htmlFor="cron" className="label">Expression cron (UTC)</label>
                <input
                  id="cron"
                  type="text"
                  value={cron}
                  onChange={(e) => setCron(e.target.value)}
                  placeholder="0 3 * * *"
                  className="input font-mono"
                  disabled={busy}
                />
                <p className="mt-1.5 text-[11px] leading-relaxed text-surface-500">
                  <span className="font-mono text-surface-400">0 3 * * *</span> = tous les jours à 03:00 UTC
                </p>
              </div>

              <div>
                <label htmlFor="schedule-mode" className="label">Mode</label>
                <select
                  id="schedule-mode"
                  value={scheduleMode}
                  onChange={(e) => setScheduleMode(e.target.value as "quick" | "full")}
                  className="input"
                  disabled={busy}
                >
                  <option value="quick">Rapide (fiabilité + sécurité)</option>
                  <option value="full">Complet (4 agents + navigateur)</option>
                </select>
              </div>

              <button type="submit" disabled={busy} className="btn-primary w-full">
                <svg
                  className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  {busy ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  )}
                </svg>
                {busy ? "Enregistrement…" : "Enregistrer la planification"}
              </button>
            </div>
          </form>

          {schedules.length > 0 && (
            <div className="card" aria-label="Planifications actives">
              <header className="panel-header">
                <h3 className="text-heading-sm font-semibold text-surface-50">Planifications actives</h3>
                <span className="numeric text-body-xs text-surface-500">{schedules.length}</span>
              </header>
              <div className="divide-y divide-surface-800/80">
                {schedules.map((schedule) => (
                  <div key={schedule.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <code className="rounded border border-surface-800 bg-surface-950 px-1.5 py-0.5 font-mono text-body-xs text-surface-300">
                        {schedule.cron}
                      </code>
                      <span className="badge badge-neutral">{schedule.mode === "quick" ? "rapide" : "complet"}</span>
                      <span className="text-[11px] text-surface-500">
                        {schedule.last_run ? timeAgo(schedule.last_run) : "jamais exécuté"}
                      </span>
                    </div>
                    <button
                      onClick={async () => {
                        await sitesApi.deleteSchedule(schedule.id);
                        load();
                      }}
                      className="btn-ghost btn-sm shrink-0 px-1.5 text-surface-500 hover:bg-danger-500/10 hover:text-danger-300"
                      title="Supprimer cette planification"
                      aria-label={`Supprimer la planification ${schedule.cron}`}
                    >
                      <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-lg border border-danger-500/20 bg-danger-500/[0.03] p-4">
            <h3 className="text-body-sm font-medium text-surface-200">Zone de danger</h3>
            <p className="mt-1 text-[11px] leading-relaxed text-surface-500">
              La suppression retire le site, ses scans et son historique.
            </p>
            <button onClick={removeSite} className="btn-danger btn-sm mt-3 w-full">
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Supprimer ce site
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
