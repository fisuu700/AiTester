"use client";

import { useEffect, useRef, useState } from "react";
import { scoreColor, scoreGrade } from "@/lib/labels";

interface Props {
  score?: number | null;
  size?: number;
  label?: string;
  showGrade?: boolean;
  animate?: boolean;
}

export default function ScoreGauge({ score, size = 96, label, showGrade = true, animate = true }: Props) {
  const stroke = size >= 100 ? 5 : 4;
  const radius = size / 2 - stroke;
  const circumference = 2 * Math.PI * radius;
  const clampedValue = Math.max(0, Math.min(100, score ?? 0));
  const offset = circumference - (clampedValue / 100) * circumference;
  const color = scoreColor(score);
  const grade = scoreGrade(score);
  const [currentOffset, setCurrentOffset] = useState(animate ? circumference : offset);
  const animatedRef = useRef(false);

  const isEmpty = score === null || score === undefined;

  useEffect(() => {
    if (!animate) return;
    if (isEmpty || animatedRef.current) return;
    animatedRef.current = true;
    const timer = setTimeout(() => setCurrentOffset(offset), 40);
    return () => clearTimeout(timer);
  }, [animate, isEmpty, offset]);

  useEffect(() => {
    if (!animate) setCurrentOffset(offset);
  }, [animate, offset]);

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="-rotate-90"
          role="img"
          aria-label={isEmpty ? "Score non disponible" : `Score : ${Math.round(score!)} sur 100`}
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#2b2f35"
            strokeWidth={stroke}
          />
          {!isEmpty && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={circumference}
              style={{
                strokeDashoffset: currentOffset,
                transition: animate ? "stroke-dashoffset 700ms cubic-bezier(0.22, 1, 0.36, 1)" : "none",
              }}
              aria-hidden="true"
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-mono font-medium leading-none tabular-nums"
            style={{
              fontSize: Math.round(size / 3.6),
              color: isEmpty ? "#545a63" : color,
              letterSpacing: "-0.02em",
            }}
          >
            {isEmpty ? "—" : Math.round(score!)}
          </span>
          {showGrade && (
            <span
              className="mt-1 font-mono text-[10px] font-medium uppercase tracking-[0.14em]"
              style={{ color: isEmpty ? "#545a63" : color }}
            >
              {isEmpty ? "n/a" : grade}
            </span>
          )}
        </div>
      </div>
      {label && (
        <span className="max-w-[130px] text-center text-[11px] font-medium uppercase tracking-[0.1em] text-surface-500">
          {label}
        </span>
      )}
    </div>
  );
}
