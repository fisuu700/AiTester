"use client";

import { AGENT_LABELS, STATUS_DOTS, STATUS_LABELS, scoreColor } from "@/lib/labels";

export interface AgentState {
  agent: string;
  label?: string;
  status: string;
  score?: number | null;
  findings?: number;
  duration_ms?: number;
  error?: string | null;
}

const AGENT_ICONS: Record<string, React.ReactNode> = {
  reliability: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  ),
  security: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  ),
  performance: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M13 10V3L4 14h7v7l9-11h-7z" />
  ),
  accessibility: (
    <>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </>
  ),
  functional: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
  ),
  analyst: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.6} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  ),
};

export default function AgentStatusGrid({ agents }: { agents: AgentState[] }) {
  if (agents.length === 0) {
    return (
      <div className="card px-6 py-10 text-center">
        <p className="text-body-sm text-surface-500">Les agents vont démarrer…</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" role="list" aria-label="Statut des agents">
      {agents.map((agent) => {
        const running = agent.status === "running";
        const hasScore = agent.score !== undefined && agent.score !== null;

        return (
          <article
            key={agent.agent}
            className={`relative overflow-hidden rounded-lg border bg-surface-900 p-3.5 ${
              running ? "border-info-500/40" : "border-surface-800"
            }`}
            role="listitem"
          >
            {running && (
              <span
                className="absolute inset-x-0 top-0 h-px animate-pulse bg-info-400/70"
                aria-hidden="true"
              />
            )}

            <header className="flex items-start justify-between gap-2">
              <div className="flex min-w-0 items-center gap-2">
                <svg
                  className={`h-4 w-4 shrink-0 ${running ? "text-info-300" : "text-surface-500"}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  {AGENT_ICONS[agent.agent] ?? AGENT_ICONS.functional}
                </svg>
                <h3 className="truncate text-body-sm font-medium text-surface-200">
                  {agent.label ?? AGENT_LABELS[agent.agent] ?? agent.agent}
                </h3>
              </div>
              {hasScore && (
                <span
                  className="numeric shrink-0 text-body-md font-medium leading-none"
                  style={{ color: scoreColor(agent.score) }}
                >
                  {Math.round(agent.score!)}
                </span>
              )}
            </header>

            <div className="mt-2.5 flex items-center justify-between gap-2 text-[11px] text-surface-500">
              <span className="inline-flex items-center gap-1.5">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${STATUS_DOTS[agent.status] ?? STATUS_DOTS.queued} ${
                    running ? "animate-pulse" : ""
                  }`}
                  aria-hidden="true"
                />
                {STATUS_LABELS[agent.status] ?? agent.status}
              </span>
              <span className="numeric truncate">
                {agent.findings ?? 0} pb
                {agent.duration_ms !== undefined ? ` · ${(agent.duration_ms / 1000).toFixed(1)}s` : ""}
              </span>
            </div>

            {agent.error && (
              <p className="mt-2.5 line-clamp-2 rounded border border-danger-500/25 bg-danger-500/5 px-2 py-1.5 font-mono text-[10px] leading-relaxed text-danger-300">
                {agent.error}
              </p>
            )}
          </article>
        );
      })}
    </div>
  );
}
