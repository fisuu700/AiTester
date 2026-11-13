"use client";

import { useState } from "react";
import type { RunRequest } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  running: boolean;
  onRun: (request: RunRequest) => void;
}

export default function RunForm({ running, onRun }: Props) {
  const [targetUrl, setTargetUrl] = useState("http://localhost:8001");
  const [scenario, setScenario] = useState("");
  const [dbUrl, setDbUrl] = useState("sqlite:///./demo_bank.db");
  const [useDb, setUseDb] = useState(true);
  const [headless, setHeadless] = useState(true);

  const submit = () => {
    if (!targetUrl.trim() || !scenario.trim()) return;
    const request: RunRequest = {
      target_url: targetUrl.trim(),
      scenario: scenario.trim(),
      headless,
    };
    if (useDb && dbUrl.trim()) request.db = { url: dbUrl.trim() };
    onRun(request);
  };

  return (
    <section className="card" aria-label="Scénario de test">
      <header className="panel-header">
        <h2 className="text-heading-sm font-semibold text-surface-50">Scénario de test</h2>
        <span className="badge badge-neutral font-mono">legacy</span>
      </header>

      <div className="space-y-4 p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="label">URL cible</span>
            <input
              className="input font-mono"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="http://localhost:8001"
              disabled={running}
            />
          </label>

          <label className="block">
            <span className="label">Connexion DB</span>
            <input
              className="input font-mono disabled:opacity-40"
              value={dbUrl}
              onChange={(e) => setDbUrl(e.target.value)}
              placeholder="sqlite:///./demo_bank.db"
              disabled={running || !useDb}
            />
          </label>
        </div>

        <label className="block">
          <span className="label">Scénario en langage naturel</span>
          <textarea
            className="input h-24 resize-none"
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            placeholder="Ex : Vérifier un virement de 500 TND du compte courant vers le compte épargne"
            disabled={running}
          />
        </label>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] text-surface-400">
          <label className="inline-flex items-center gap-2">
            <input
              id="use-db"
              type="checkbox"
              checked={useDb}
              onChange={(e) => setUseDb(e.target.checked)}
              disabled={running}
              className="h-3.5 w-3.5 accent-brand-400"
            />
            Validation base de données (lecture seule)
          </label>
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={headless}
              onChange={(e) => setHeadless(e.target.checked)}
              disabled={running}
              className="h-3.5 w-3.5 accent-brand-400"
            />
            Navigateur headless
          </label>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-800 pt-4">
          <p className="font-mono text-[11px] text-surface-600">
            backend <span className="text-surface-400">{API_URL}</span>
          </p>
          <button
            onClick={submit}
            disabled={running || !targetUrl.trim() || !scenario.trim()}
            className="btn-primary btn-sm"
          >
            {running ? "Exécution…" : "Lancer le test"}
          </button>
        </div>
      </div>
    </section>
  );
}
