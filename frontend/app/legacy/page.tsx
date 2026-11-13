"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";

import LogStream from "@/components/LogStream";
import ReportViewer from "@/components/ReportViewer";
import RunForm from "@/components/RunForm";
import type { LogEvent, RunReport, RunRequest, WsMessage } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LegacyPage() {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [report, setReport] = useState<RunReport | null>(null);
  const [running, setRunning] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const startRun = useCallback((request: RunRequest) => {
    setEvents([]);
    setReport(null);
    setRunning(true);

    const ws = new WebSocket(`ws://${API_URL.replace(/^https?:\/\//, "")}/ws/run`);
    wsRef.current = ws;

    ws.onopen = () => ws.send(JSON.stringify(request));
    ws.onmessage = (message) => {
      try {
        const data: WsMessage = JSON.parse(message.data);
        if (data.type === "log") {
          setEvents((prev) => [...prev, data.event]);
        } else if (data.type === "report") {
          setReport(data.report);
        } else if (data.type === "error") {
          setEvents((prev) => [
            ...prev,
            { ts: new Date().toISOString(), level: "error", message: data.message, data: {} },
          ]);
        }
      } catch {
        // ignore malformed messages
      }
    };
    ws.onclose = () => setRunning(false);
    ws.onerror = () => {
      setEvents((prev) => [
        ...prev,
        {
          ts: new Date().toISOString(),
          level: "error",
          message: "Connexion WebSocket échouée — backend démarré sur le port 8000 ?",
          data: {},
        },
      ]);
      setRunning(false);
    };
  }, []);

  return (
    <main className="container-app space-y-6 py-8">
      <Link href="/" className="btn-ghost btn-sm -ml-2 gap-1.5">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Tableau de bord
      </Link>

      <header>
        <p className="eyebrow">Interface historique</p>
        <h1 className="mt-1 text-heading-xl font-semibold">Agent autonome E2E</h1>
        <p className="mt-1.5 max-w-2xl text-body-sm text-surface-500">
          Vérification tri-couche pilotée par l&apos;IA — UI · API · base de données.
          <span className="ml-1 font-mono text-[11px] text-surface-600">
            llama3.1:8b · qwen2.5-coder:7b · deepseek-r1:7b via Ollama
          </span>
        </p>
      </header>

      <RunForm running={running} onRun={startRun} />
      <LogStream events={events} running={running} />
      {report && <ReportViewer report={report} />}
    </main>
  );
}
