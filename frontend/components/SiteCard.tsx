"use client";

import Link from "next/link";

import { timeAgo } from "@/lib/api";
import { STATUS_DOTS, STATUS_LABELS } from "@/lib/labels";
import type { Site } from "@/lib/types";
import ScoreGauge from "./ScoreGauge";

interface SiteCardProps {
  site: Site;
  className?: string;
}

export default function SiteCard({ site, className = "" }: SiteCardProps) {
  const last = site.last_scan;
  const status = last?.status ?? "queued";

  return (
    <Link
      href={`/sites/${site.id}`}
      className={`group card card-hover flex flex-col p-4 ${className}`}
      aria-label={site.name ? `Voir ${site.name}` : `Voir ${site.url}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="truncate text-body-md font-medium text-surface-50 transition-colors group-hover:text-brand-300">
            {site.name || site.url}
          </h3>
          <p className="mt-0.5 truncate font-mono text-[11px] leading-relaxed text-surface-500">
            {site.url}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-surface-500">
            <span className="inline-flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOTS[status] ?? STATUS_DOTS.queued}`} aria-hidden="true" />
              {last ? (STATUS_LABELS[status] ?? status) : "Jamais scanné"}
            </span>
            {last && (
              <>
                <span className="numeric">{last.findings_count} problèmes</span>
                {last.critical_count > 0 && (
                  <span className="numeric text-danger-300">{last.critical_count} critiques</span>
                )}
                <span>{timeAgo(last.created_at)}</span>
              </>
            )}
          </div>
        </div>

        <ScoreGauge score={last?.global_score} size={56} showGrade={false} />
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-surface-800 pt-2.5 text-[11px] text-surface-500">
        <span className="numeric">{site.scans_count} scan(s)</span>
        <span className="flex items-center gap-1 text-surface-500 transition-colors group-hover:text-brand-300">
          Ouvrir
          <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </span>
      </div>
    </Link>
  );
}
