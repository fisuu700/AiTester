"use client";

import { SEVERITY_DOTS, SEVERITY_LABELS } from "@/lib/labels";

/** Pastille de sévérité : point coloré + libellé (style outil, sans icône). */
export default function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.08em] text-surface-400">
      <span
        className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOTS[severity] ?? SEVERITY_DOTS.info}`}
        aria-hidden="true"
      />
      {SEVERITY_LABELS[severity] ?? severity}
    </span>
  );
}
