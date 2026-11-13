"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { ApiError, formatDate, scansApi, timeAgo } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { STATUS_DOTS, STATUS_LABELS } from "@/lib/labels";
import type { ScanSummary } from "@/lib/types";

export default function ScansPage() {
  const { user, loading } = useRequireAuth();
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setScans(await scansApi.list(100));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    }
  }, []);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  if (loading || !user) {
    return (
      <main className="container-app flex min-h-[60vh] items-center justify-center py-16">
        <div className="flex items-center gap-3 text-body-sm text-surface-500">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border border-surface-700 border-t-brand-400" aria-hidden="true" />
          Chargement de l&apos;historique…
        </div>
      </main>
    );
  }

  return (
    <main className="container-app space-y-6 py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Journal</p>
          <h1 className="mt-1 text-heading-xl font-semibold">Historique des scans</h1>
          <p className="mt-1 text-body-sm text-surface-500">
            Tous les scans exécutés sur vos sites.
          </p>
        </div>
        <Link href="/" className="btn-secondary btn-sm shrink-0">
          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Tableau de bord
        </Link>
      </header>

      {error && (
        <p className="card border-danger-500/30 bg-danger-500/5 px-4 py-3 text-body-sm text-danger-300" role="alert">
          {error}
        </p>
      )}

      {scans.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <h3 className="empty-state-title">Aucun scan pour l&apos;instant</h3>
          <p className="empty-state-description">
            Lancez un scan depuis un site pour alimenter cet historique.
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="hidden grid-cols-[7rem_1fr_5rem_5rem_4rem] gap-3 border-b border-surface-800 bg-surface-925 px-4 py-2 text-[11px] font-medium uppercase tracking-[0.12em] text-surface-500 sm:grid">
            <span>Statut</span>
            <span>Scan</span>
            <span>Mode</span>
            <span className="text-right">Problèmes</span>
            <span className="text-right">Score</span>
          </div>

          <div className="divide-y divide-surface-800/80">
            {scans.map((scan) => (
              <Link
                key={scan.id}
                href={`/scans/${scan.id}`}
                className="grid grid-cols-[1fr_auto] items-center gap-3 px-4 py-3 transition-colors hover:bg-surface-850/50 sm:grid-cols-[7rem_1fr_5rem_5rem_4rem]"
              >
                <span className="hidden items-center gap-1.5 text-[11px] text-surface-400 sm:inline-flex">
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${STATUS_DOTS[scan.status] ?? STATUS_DOTS.queued} ${
                      scan.status === "running" ? "animate-pulse" : ""
                    }`}
                    aria-hidden="true"
                  />
                  {STATUS_LABELS[scan.status] ?? scan.status}
                </span>

                <span className="min-w-0">
                  <span className="block truncate font-mono text-body-xs text-surface-200">{scan.id}</span>
                  <span className="mt-0.5 block text-[11px] text-surface-500">
                    {timeAgo(scan.created_at)} · {formatDate(scan.created_at)}
                  </span>
                </span>

                <span className="hidden text-body-xs text-surface-400 sm:block">
                  {scan.mode === "quick" ? "rapide" : "complet"}
                </span>

                <span className="hidden text-right text-body-xs sm:block">
                  <span className="numeric text-surface-300">{scan.findings_count}</span>
                  {scan.critical_count > 0 && (
                    <span className="numeric ml-1 text-danger-300">({scan.critical_count})</span>
                  )}
                </span>

                <span className="numeric text-right text-body-sm font-medium text-surface-100">
                  {scan.global_score === null || scan.global_score === undefined
                    ? "—"
                    : Math.round(scan.global_score)}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
