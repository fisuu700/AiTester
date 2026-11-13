"use client";

import { useState } from "react";

import { ApiError, sitesApi } from "@/lib/api";
import type { Site } from "@/lib/types";

interface Props {
  onCreated: (site: Site) => void;
}

export default function AddSiteForm({ onCreated }: Props) {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [urlError, setUrlError] = useState<string | null>(null);

  const validateUrl = (value: string) => {
    if (!value.trim()) return null;
    try {
      new URL(value.trim());
      return null;
    } catch {
      return "URL invalide (ex : https://example.com)";
    }
  };

  const handleUrlChange = (value: string) => {
    setUrl(value);
    setUrlError(validateUrl(value));
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const urlErr = validateUrl(url);
    if (urlErr || !url.trim() || !consent) return;

    setBusy(true);
    setError(null);
    try {
      const site = await sitesApi.create(url.trim(), name.trim(), consent);
      onCreated(site);
      setUrl("");
      setName("");
      setConsent(false);
      setUrlError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'ajouter ce site.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="card" noValidate>
      <header className="panel-header">
        <div>
          <h2 className="text-heading-sm font-semibold text-surface-50">Ajouter un site</h2>
          <p className="mt-0.5 text-[11px] text-surface-500">
            Les agents couvrent fiabilité, sécurité, performance et accessibilité.
          </p>
        </div>
        <span className="badge badge-neutral font-mono">nouveau</span>
      </header>

      <div className="space-y-3 p-4">
        <div className="grid items-start gap-2.5 sm:grid-cols-[minmax(0,1fr)_180px_auto]">
          <div>
            <label htmlFor="site-url" className="label">URL</label>
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-[11px] text-surface-600">
                https://
              </span>
              <input
                id="site-url"
                type="url"
                value={url}
                onChange={(e) => handleUrlChange(e.target.value)}
                placeholder="mon-site.tn"
                required
                disabled={busy}
                className={`input pl-[58px] font-mono ${urlError ? "input-error" : ""}`}
                aria-describedby={urlError ? "url-error" : undefined}
                aria-invalid={!!urlError}
              />
            </div>
          </div>

          <div>
            <label htmlFor="site-name" className="label">Nom · optionnel</label>
            <input
              id="site-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Mon site"
              disabled={busy}
              className="input"
            />
          </div>

          <div className="sm:pt-[22px]">
            <button
              type="submit"
              disabled={busy || !url.trim() || !!urlError || !consent}
              className="btn-primary w-full sm:w-auto"
            >
              {busy ? (
                <>
                  <svg className="h-3.5 w-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Ajout…
                </>
              ) : (
                "Ajouter"
              )}
            </button>
          </div>
        </div>

        {urlError && (
          <p id="url-error" className="text-[11px] text-danger-300" role="alert">
            {urlError}
          </p>
        )}

        <label className="flex cursor-pointer items-start gap-2.5 text-[11px] leading-relaxed text-surface-500">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-px h-3.5 w-3.5 shrink-0 accent-brand-400"
            required
          />
          <span>
            Je certifie être propriétaire de ce site ou disposer d&apos;une autorisation écrite
            pour le tester. Les scans sont strictement <strong className="font-medium text-surface-300">passifs</strong>.
          </span>
        </label>

        {error && (
          <p
            className="rounded-md border border-danger-500/30 bg-danger-500/5 px-3 py-2 text-body-xs text-danger-300 animate-fade-in"
            role="alert"
          >
            {error}
          </p>
        )}
      </div>
    </form>
  );
}
