"use client";

import { useState } from "react";
import Link from "next/link";

import { ApiError, authApi, formatDate } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { User } from "@/lib/types";

export default function AccountPage() {
  const { user, loading, refresh } = useRequireAuth();
  const [current, setCurrent] = useState<User | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const account = current ?? user;

  const generateKey = async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await authApi.createApiKey();
      setCurrent(updated);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Génération impossible.");
    } finally {
      setBusy(false);
    }
  };

  const revokeKey = async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await authApi.revokeApiKey();
      setCurrent(updated);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Révocation impossible.");
    } finally {
      setBusy(false);
    }
  };

  const copyKey = async () => {
    if (!account?.api_key) return;
    await navigator.clipboard.writeText(account.api_key);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  if (loading || !account) {
    return (
      <main className="container-app flex min-h-[60vh] items-center justify-center py-16">
        <div className="flex items-center gap-3 text-body-sm text-surface-500">
          <span
            className="h-3.5 w-3.5 animate-spin rounded-full border border-surface-700 border-t-brand-400"
            aria-hidden="true"
          />
          Chargement du compte…
        </div>
      </main>
    );
  }

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  return (
    <main className="container-app max-w-3xl space-y-6 py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Compte</p>
          <h1 className="mt-1 text-heading-xl font-semibold">Informations et accès</h1>
          <p className="mt-1 text-body-sm text-surface-500">
            Identité, clé API et interface historique.
          </p>
        </div>
        <Link href="/" className="btn-secondary btn-sm shrink-0">
          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Tableau de bord
        </Link>
      </header>

      <section className="card" aria-label="Informations du compte">
        <header className="panel-header">
          <h2 className="text-heading-sm font-semibold text-surface-50">Identité</h2>
        </header>
        <dl className="grid gap-5 px-5 py-4 sm:grid-cols-2">
          <div>
            <dt className="eyebrow">Email</dt>
            <dd className="mt-1 break-all text-body-sm font-medium text-surface-100">{account.email}</dd>
          </div>
          <div>
            <dt className="eyebrow">Membre depuis</dt>
            <dd className="mt-1 text-body-sm text-surface-200">{formatDate(account.created_at)}</dd>
          </div>
        </dl>
      </section>

      <section className="card" aria-label="Clé API">
        <header className="panel-header">
          <div>
            <h2 className="text-heading-sm font-semibold text-surface-50">Clé API</h2>
            <p className="mt-0.5 text-[11px] text-surface-500">
              Pour lancer un scan depuis une pipeline CI/CD.
            </p>
          </div>
          <span className="badge badge-neutral font-mono">X-API-Key</span>
        </header>

        <div className="space-y-4 px-5 py-4">
          {account.api_key ? (
            <div className="flex flex-wrap items-stretch gap-2">
              <code className="min-w-[200px] flex-1 overflow-x-auto rounded-md border border-surface-800 bg-surface-950 px-3 py-2 font-mono text-body-xs leading-6 text-brand-300">
                {account.api_key}
              </code>
              <button
                onClick={copyKey}
                className="btn-secondary btn-sm shrink-0"
                aria-label={copied ? "Clé copiée" : "Copier la clé API"}
              >
                {copied ? "Copié" : "Copier"}
              </button>
              <button onClick={revokeKey} disabled={busy} className="btn-danger btn-sm shrink-0">
                Révoquer
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-body-xs text-surface-500">Aucune clé active pour ce compte.</p>
              <button onClick={generateKey} disabled={busy} className="btn-primary btn-sm">
                {busy ? (
                  <>
                    <svg className="h-3.5 w-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Génération…
                  </>
                ) : (
                  "Générer une clé"
                )}
              </button>
            </div>
          )}

          {error && (
            <p
              className="rounded-md border border-danger-500/30 bg-danger-500/5 px-3 py-2 text-body-xs text-danger-300 animate-fade-in"
              role="alert"
            >
              {error}
            </p>
          )}

          <div className="overflow-x-auto rounded-md border border-surface-800 bg-surface-950">
            <div className="flex items-center justify-between border-b border-surface-800 px-3 py-1.5">
              <span className="eyebrow">Exemple</span>
              <span className="font-mono text-[10px] text-surface-600">cURL</span>
            </div>
            <pre className="px-3 py-2.5 font-mono text-[11px] leading-relaxed text-surface-400"><code>{`curl -X POST ${apiBase}/api/scans \\
  -H "X-API-Key: ${account.api_key ?? "VOTRE_CLE"}" \\
  -H "Content-Type: application/json" \\
  -d '{"url":"https://mon-site.tn","mode":"quick"}'`}</code></pre>
          </div>
        </div>
      </section>

      <section className="card" aria-label="Agent E2E historique">
        <header className="panel-header">
          <div>
            <h2 className="text-heading-sm font-semibold text-surface-50">Agent E2E historique</h2>
            <p className="mt-0.5 text-[11px] text-surface-500">
              Scénario UI · API · DB piloté par Ollama.
            </p>
          </div>
          <span className="badge badge-neutral">legacy</span>
        </header>
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
          <p className="max-w-md text-body-xs leading-relaxed text-surface-500">
            L&apos;interface d&apos;origine reste disponible pour les scénarios avancés.
          </p>
          <Link href="/legacy" className="btn-secondary btn-sm shrink-0">
            Ouvrir
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      </section>
    </main>
  );
}
