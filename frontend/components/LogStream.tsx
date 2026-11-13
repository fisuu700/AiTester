"use client";

import { useEffect, useRef } from "react";
import type { LogEvent } from "@/lib/types";

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

interface Props {
  events: LogEvent[];
  running: boolean;
}

export default function LogStream({ events, running }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <section className="card flex h-[380px] flex-col overflow-hidden" aria-label="Logs en direct">
      <header className="panel-header">
        <h2 className="text-heading-sm font-semibold text-surface-50">Logs en direct</h2>
        {running ? (
          <span className="inline-flex items-center gap-1.5 text-[11px] text-info-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-info-400" aria-hidden="true" />
            en cours
          </span>
        ) : (
          <span className="numeric text-[11px] text-surface-500">{events.length} événements</span>
        )}
      </header>

      <div className="flex-1 overflow-y-auto bg-surface-950 px-4 py-3 font-mono text-[11px] leading-relaxed" role="log" aria-live="polite">
        {events.length === 0 && (
          <p className="px-1 py-10 text-center text-surface-500">
            Aucun événement — lancez un scénario pour voir les logs.
          </p>
        )}

        <div className="space-y-1">
          {events.map((event, i) => (
            <div key={i} className="flex items-start gap-2.5">
              <span className="w-[68px] shrink-0 tabular-nums text-surface-600">
                {new Date(event.ts).toLocaleTimeString("fr-FR", { hour12: false })}
              </span>
              <span className={`shrink-0 ${LEVEL_MARK[event.level] ?? LEVEL_MARK.info}`} aria-hidden="true">
                ·
              </span>
              <span className={`break-all ${LEVEL_STYLE[event.level] ?? LEVEL_STYLE.info}`}>
                {event.message}
              </span>
            </div>
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
