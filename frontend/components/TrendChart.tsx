"use client";

import { scoreColor } from "@/lib/labels";
import type { HistoryPoint } from "@/lib/types";

const WIDTH = 640;
const HEIGHT = 190;
const PADDING = 30;
const AXIS_LEFT = 26;

export default function TrendChart({ points }: { points: HistoryPoint[] }) {
  const usable = points.filter((point) => point.global_score !== null && point.global_score !== undefined);

  if (usable.length < 2) {
    return (
      <div className="card flex items-center justify-between gap-4 px-4 py-5">
        <div>
          <h2 className="text-heading-sm font-semibold text-surface-50">Évolution du score</h2>
          <p className="mt-0.5 text-body-xs text-surface-500">
            Au moins deux scans terminés sont nécessaires.
          </p>
        </div>
        <span className="numeric rounded border border-surface-800 bg-surface-925 px-2 py-1 text-[11px] text-surface-500">
          {usable.length}/2
        </span>
      </div>
    );
  }

  const innerWidth = WIDTH - AXIS_LEFT - PADDING;
  const innerHeight = HEIGHT - PADDING * 2;
  const step = innerWidth / (usable.length - 1);

  const coords = usable.map((point, index) => {
    const score = Math.max(0, Math.min(100, point.global_score ?? 0));
    return {
      x: AXIS_LEFT + index * step,
      y: PADDING + innerHeight - (score / 100) * innerHeight,
      score,
      date: point.created_at,
    };
  });

  const line = coords.map((coord) => `${coord.x},${coord.y}`).join(" ");
  const area = `${AXIS_LEFT},${PADDING + innerHeight} ${line} ${AXIS_LEFT + innerWidth},${PADDING + innerHeight}`;
  const last = coords[coords.length - 1];

  return (
    <section className="card overflow-hidden" aria-label="Évolution du score global">
      <header className="panel-header">
        <h2 className="text-heading-sm font-semibold text-surface-50">Évolution du score</h2>
        <div className="flex items-center gap-3">
          <span className="numeric text-body-xs text-surface-400">
            dernier <span style={{ color: scoreColor(last.score) }}>{Math.round(last.score)}</span>/100
          </span>
          <span className="numeric rounded border border-surface-800 bg-surface-925 px-1.5 py-0.5 text-[10px] text-surface-500">
            {usable.length} scans
          </span>
        </div>
      </header>

      <div className="px-1 py-2">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="w-full"
          role="img"
          aria-label={`Graphique d'évolution du score global sur ${usable.length} scans. Score actuel : ${Math.round(last.score)} sur 100.`}
        >
          {[0, 25, 50, 75, 100].map((value) => {
            const y = PADDING + innerHeight - (value / 100) * innerHeight;
            return (
              <g key={value}>
                <line
                  x1={AXIS_LEFT}
                  y1={y}
                  x2={WIDTH - PADDING}
                  y2={y}
                  stroke="#2b2f35"
                  strokeWidth={1}
                  strokeDasharray={value === 0 ? undefined : "3,4"}
                />
                <text
                  x={AXIS_LEFT - 8}
                  y={y + 3}
                  fill="#545a63"
                  fontSize={9}
                  fontFamily="JetBrains Mono, monospace"
                  textAnchor="end"
                >
                  {value}
                </text>
              </g>
            );
          })}

          {coords.map((coord, index) => {
            const stride = Math.max(1, Math.ceil(coords.length / 6));
            if (index % stride !== 0 && index !== coords.length - 1) return null;
            return (
              <g key={`x-${index}`}>
                <line
                  x1={coord.x}
                  y1={PADDING}
                  x2={coord.x}
                  y2={PADDING + innerHeight}
                  stroke="#23262b"
                  strokeWidth={1}
                />
                <text
                  x={coord.x}
                  y={HEIGHT - 8}
                  fill="#545a63"
                  fontSize={9}
                  fontFamily="JetBrains Mono, monospace"
                  textAnchor="middle"
                >
                  {new Date(coord.date).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" })}
                </text>
              </g>
            );
          })}

          <polygon points={area} fill="#3ed287" fillOpacity={0.07} />
          <polyline
            points={line}
            fill="none"
            stroke="#3ed287"
            strokeWidth={1.75}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {coords.map((coord, index) => (
            <circle
              key={`p-${index}`}
              cx={coord.x}
              cy={coord.y}
              r={2.5}
              fill={scoreColor(coord.score)}
              stroke="#0e1013"
              strokeWidth={1.5}
            >
              <title>{`${Math.round(coord.score)}/100 — ${new Date(coord.date).toLocaleDateString("fr-FR")}`}</title>
            </circle>
          ))}
        </svg>
      </div>
    </section>
  );
}
