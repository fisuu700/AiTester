"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import AddSiteForm from "@/components/AddSiteForm";
import ScoreGauge from "@/components/ScoreGauge";
import SiteCard from "@/components/SiteCard";
import { ApiError, formatDate, scansApi, sitesApi, timeAgo } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { STATUS_DOTS, STATUS_LABELS } from "@/lib/labels";
import type { ScanSummary, Site } from "@/lib/types";

export default function DashboardPage() {
  const { user, loading } = useRequireAuth();
  const [sites, setSites] = useState<Site[]>([]);
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [refreshing, setRefreshing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const [siteList, scanList] = await Promise.all([sitesApi.list(), scansApi.list(8)]);
      setSites(siteList);
      setScans(scanList);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Chargement impossible.");
    } finally {
      setRefreshing(false);
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
          Chargement du tableau de bord…
        </div>
      </main>
    );
  }

  const scored = sites
    .map((site) => site.last_scan?.global_score)
    .filter((score): score is number => score !== null && score !== undefined);
  const average = scored.length
    ? Math.round(scored.reduce((total, score) => total + score, 0) / scored.length)
    : null;
  const criticals = sites.reduce((total, site) => total + (site.last_scan?.critical_count ?? 0), 0);
  const findings = sites.reduce((total, site) => total + (site.last_scan?.findings_count ?? 0), 0);

  return (
    <main className="container-app space-y-9 py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Vue d&apos;ensemble</p>
          <h1 className="mt-1 text-heading-xl font-semibold">Tableau de bord</h1>
          <p className="mt-1 text-body-sm text-surface-500">
            Fiabilité · sécurité · performance · accessibilité
          </p>
        </div>
        <button onClick={load} disabled={refreshing} className="btn-secondary btn-sm shrink-0">
          <svg className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {refreshing ? "Actualisation…" : "Actualiser"}
        </button>
      </header>

      <section
        className="card grid divide-y divide-surface-800 sm:grid-cols-3 sm:divide-x sm:divide-y-0"
        aria-label="Statistiques globales"
      >
        <div className="flex items-center gap-4 p-4">
          <ScoreGauge score={average} size={54} showGrade={false} />
          <div className="min-w-0">
            <p className="eyebrow">Score moyen</p>
            <p className="numeric mt-1 text-display-sm font-medium leading-none text-surface-50">
              {average ?? "—"}
            </p>
            <p className="mt-1.5 text-body-xs text-surface-500">
              {sites.length} site{sites.length > 1 ? "s" : ""} suivi{sites.length > 1 ? "s" : ""}
            </p>
          </div>
        </div>

        <div className="p-4">
          <p className="eyebrow">Problèmes ouverts</p>
          <p className="numeric mt-1 text-display-sm font-medium leading-none text-surface-50">{findings}</p>
          <p className="mt-1.5 text-body-xs text-surface-500">sur le dernier scan de chaque site</p>
        </div>

        <div className="p-4">
          <p className="eyebrow">Critiques</p>
          <p
            className={`numeric mt-1 text-display-sm font-medium leading-none ${
              criticals > 0 ? "text-danger-300" : "text-surface-50"
            }`}
          >
            {criticals}
          </p>
          <p className="mt-1.5 text-body-xs text-surface-500">
            {criticals > 0 ? "à traiter en priorité" : "aucun bloquant détecté"}
          </p>
        </div>
      </section>

      <AddSiteForm
        onCreated={(site) => {
          setSites((previous) => [site, ...previous]);
          load();
        }}
      />

      {error && (
        <p className="card border-danger-500/30 bg-danger-500/5 px-4 py-3 text-body-sm text-danger-300" role="alert">
          {error}
        </p>
      )}

      <section className="space-y-4" aria-label="Mes sites">
        <header className="section-header">
          <div>
            <h2 className="section-title">Sites surveillés</h2>
            <p className="section-subtitle">{sites.length} site(s) configuré(s)</p>
          </div>
          {sites.length > 0 && (
            <Link href="/scans" className="btn-ghost btn-sm">
              Historique complet
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          )}
        </header>

        {sites.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="empty-state-title">Aucun site pour le moment</h3>
            <p className="empty-state-description">
              Ajoutez une URL ci-dessus pour lancer votre premier scan.
            </p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" role="list">
            {sites.map((site, index) => (
              <SiteCard key={site.id} site={site} className={`stagger-${(index % 6) + 1}`} />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4" aria-label="Derniers scans">
        <header className="section-header">
          <div>
            <h2 className="section-title">Derniers scans</h2>
            <p className="section-subtitle">Activité récente</p>
          </div>
          <Link href="/scans" className="btn-ghost btn-sm">
            Tout voir
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </header>

        {scans.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <h3 className="empty-state-title">Aucun scan exécuté</h3>
            <p className="empty-state-description">
              Lancez un scan depuis un site pour voir les résultats ici.
            </p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            <div className="divide-y divide-surface-800/80">
              {scans.map((scan) => (
                <Link
                  key={scan.id}
                  href={`/scans/${scan.id}`}
                  className="group flex items-center gap-4 px-4 py-3 transition-colors hover:bg-surface-850/50"
                >
                  <span className="inline-flex w-24 shrink-0 items-center gap-1.5 text-[11px] text-surface-400">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${STATUS_DOTS[scan.status] ?? STATUS_DOTS.queued} ${
                        scan.status === "running" ? "animate-pulse" : ""
                      }`}
                      aria-hidden="true"
                    />
                    {STATUS_LABELS[scan.status] ?? scan.status}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-mono text-body-xs text-surface-300">{scan.id}</p>
                    <p className="text-[11px] text-surface-500">
                      {timeAgo(scan.created_at)} · {scan.mode === "quick" ? "rapide" : "complet"}
                    </p>
                  </div>
                  <div className="hidden shrink-0 items-center gap-3 text-[11px] text-surface-500 sm:flex">
                    <span className="numeric">{scan.findings_count} pb</span>
                    {scan.critical_count > 0 && (
                      <span className="numeric text-danger-300">{scan.critical_count} crit.</span>
                    )}
                  </div>
                  <span className="numeric w-9 shrink-0 text-right text-body-sm font-medium text-surface-100">
                    {scan.global_score === null || scan.global_score === undefined
                      ? "—"
                      : Math.round(scan.global_score)}
                  </span>
                  <svg className="h-3.5 w-3.5 shrink-0 text-surface-700 transition-colors group-hover:text-surface-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              ))}
            </div>
          </div>
        )}
      </section>

      <footer className="border-t border-surface-800 pt-5 text-center text-[11px] text-surface-600">
        Dernière actualisation : {formatDate(new Date().toISOString())}
      </footer>
    </main>
  );
}
