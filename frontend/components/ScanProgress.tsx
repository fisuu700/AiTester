"use client";

import { useEffect, useRef, useState } from "react";

import { getToken, wsUrl } from "@/lib/api";
import { scoreColor } from "@/lib/labels";
import type { ServerEvent } from "@/lib/types";

interface Props {
  scanId: string;
  onEvent?: (event: ServerEvent) => void;
  onDone?: (event: ServerEvent) => void;
}

const LEVEL_STYLE: Record<string, string> = {
  info: "text-surface-300",
  warning: "text-warning-300",
  error: "text-danger-300",
};

const LEVEL_MARK: Record<string, string> = {
  info: "text-surface-600",
  warning: "text-warning-400",
  error: "text-danger-400",
};

export default function ScanProgress({ scanId, onEvent, onDone }: Props) {
  const [events, setEvents] = useState<ServerEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const eventsRef = useRef<ServerEvent[]>([]);

  const eventCallback = useRef(onEvent);
  const doneCallback = useRef(onDone);
  eventCallback.current = onEvent;
  doneCallback.current = onDone;

  useEffect(() => {
    const token = getToken() ?? "";
    const socket = new WebSocket(
      wsUrl(`/ws/scans/${scanId}?token=${encodeURIComponent(token)}`)
    );

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);

    socket.onmessage = (message) => {
      let event: ServerEvent;
      try {
        event = JSON.parse(message.data) as ServerEvent;
      } catch {
        return;
      }

      eventsRef.current = [...eventsRef.current.slice(-299), event];
      setEvents(eventsRef.current);
      eventCallback.current?.(event);

      if (event.type === "scan_done") {
        doneCallback.current?.(event);
        socket.close();
      }
    };

    return () => socket.close();
  }, [scanId]);

  return (
    <div className="space-y-2.5" aria-label="Journal du scan" role="log" aria-live="polite">
      <div className="flex items-center justify-between text-[11px]">
        <span className={`inline-flex items-center gap-1.5 ${connected ? "text-info-300" : "text-surface-500"}`}>
          <span
            className={`h-1.5 w-1.5 rounded-full ${connected ? "animate-pulse bg-info-400" : "bg-surface-600"}`}
            aria-hidden="true"
          />
          {connected ? "flux connecté" : "flux interrompu"}
        </span>
        <span className="numeric text-surface-500">{events.length} événements</span>
      </div>

      <div className="max-h-80 space-y-1 overflow-y-auto rounded-md border border-surface-800 bg-surface-950 p-3 font-mono text-[11px] leading-relaxed">
        {events.length === 0 && (
          <p className="px-1 py-6 text-center text-surface-500">
            En attente des premiers événements…
          </p>
        )}

        {events.map((event, index) => {
          if (event.type === "log") {
            const level = String(event.level ?? "info");
            return (
              <div key={index} className="flex items-start gap-2.5">
                <span className="w-[68px] shrink-0 tabular-nums text-surface-600">
                  {new Date(String(event.ts ?? Date.now())).toLocaleTimeString("fr-FR", { hour12: false })}
                </span>
                <span className={`shrink-0 ${LEVEL_MARK[level] ?? LEVEL_MARK.info}`} aria-hidden="true">
                  ·
                </span>
                <span className={`break-all ${LEVEL_STYLE[level] ?? LEVEL_STYLE.info}`}>
                  {String(event.message ?? "")}
                </span>
              </div>
            );
          }

          if (event.type === "agent_start") {
            return (
              <div
                key={index}
                className="flex items-center gap-2 rounded border border-info-500/25 bg-info-500/[0.06] px-2.5 py-1.5 animate-fade-in"
                role="status"
              >
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-info-400" aria-hidden="true" />
                <span className="text-info-300">démarrage</span>
                <span className="text-surface-200">{String(event.label ?? event.agent)}</span>
              </div>
            );
          }

          if (event.type === "agent_done") {
            const status = String(event.status ?? "completed");
            const isSuccess = status === "completed";
            return (
              <div
                key={index}
                className={`flex flex-wrap items-center gap-x-3 gap-y-1 rounded border px-2.5 py-1.5 animate-fade-in ${
                  isSuccess
                    ? "border-brand-500/25 bg-brand-500/[0.05]"
                    : "border-danger-500/30 bg-danger-500/[0.06]"
                }`}
                role="status"
              >
                <span className={`${isSuccess ? "text-brand-300" : "text-danger-300"}`}>
                  {isSuccess ? "terminé" : "échec"}
                </span>
                <span className="text-surface-200">{String(event.label ?? event.agent)}</span>
                <span className="ml-auto flex items-center gap-3 text-surface-500">
                  <span className="numeric">{String(event.findings ?? 0)} pb</span>
                  {event.score !== null && event.score !== undefined && (
                    <span
                      className="numeric font-medium"
                      style={{ color: scoreColor(Number(event.score)) }}
                    >
                      {Math.round(Number(event.score))}
                    </span>
                  )}
                </span>
              </div>
            );
          }

          if (event.type === "scan_done") {
            const status = String(event.status);
            const isSuccess = status === "completed";
            return (
              <div
                key={index}
                className={`flex flex-wrap items-center gap-3 rounded border px-3 py-2 animate-fade-in ${
                  isSuccess
                    ? "border-brand-500/30 bg-brand-500/[0.06]"
                    : "border-danger-500/30 bg-danger-500/[0.06]"
                }`}
                role="status"
              >
                <span className={`font-medium ${isSuccess ? "text-brand-300" : "text-danger-300"}`}>
                  scan {isSuccess ? "terminé" : "échoué"}
                </span>
                <span className="text-surface-500">statut : {status}</span>
                {event.global_score !== null && event.global_score !== undefined && (
                  <span className="ml-auto flex items-baseline gap-1.5">
                    <span className="text-[10px] uppercase tracking-[0.1em] text-surface-600">score</span>
                    <span
                      className="numeric text-body-md font-medium"
                      style={{ color: scoreColor(Number(event.global_score)) }}
                    >
                      {Math.round(Number(event.global_score))}
                    </span>
                  </span>
                )}
              </div>
            );
          }

          return null;
        })}
      </div>
    </div>
  );
}
