export const AGENT_LABELS: Record<string, string> = {
  reliability: "Fiabilité",
  security: "Sécurité",
  performance: "Performance",
  accessibility: "Accessibilité",
  functional: "Fonctionnel",
  analyst: "Analyse IA",
};

export const AGENT_SHORT: Record<string, string> = {
  reliability: "Fiab.",
  security: "Sécu.",
  performance: "Perf.",
  accessibility: "Acc.",
  functional: "Fonct.",
  analyst: "Analyste",
};

export const SEVERITY_LABELS: Record<string, string> = {
  critical: "Critique",
  high: "Élevé",
  medium: "Moyen",
  low: "Faible",
  info: "Info",
};

export const SEVERITY_CLASSES: Record<string, string> = {
  critical: "border-danger-500/40 bg-danger-500/10 text-danger-300",
  high: "border-accent-500/40 bg-accent-500/10 text-accent-300",
  medium: "border-warning-500/40 bg-warning-500/10 text-warning-300",
  low: "border-info-500/40 bg-info-500/10 text-info-300",
  info: "border-surface-700 bg-surface-850 text-surface-400",
};

export const SEVERITY_DOTS: Record<string, string> = {
  critical: "bg-danger-400",
  high: "bg-accent-400",
  medium: "bg-warning-400",
  low: "bg-info-400",
  info: "bg-surface-500",
};

export function scoreColor(score?: number | null): string {
  if (score === null || score === undefined) return "#6c737c";
  if (score >= 90) return "#3ed287";
  if (score >= 75) return "#9ed36a";
  if (score >= 60) return "#e6ac4c";
  if (score >= 40) return "#e8845a";
  return "#ea7462";
}

export function scoreGrade(score?: number | null): string {
  if (score === null || score === undefined) return "?";
  if (score >= 90) return "A";
  if (score >= 75) return "B";
  if (score >= 60) return "C";
  if (score >= 40) return "D";
  return "E";
}

export const STATUS_CLASSES: Record<string, string> = {
  queued: "border-surface-700 bg-surface-850 text-surface-400",
  running: "border-info-500/40 bg-info-500/10 text-info-300",
  completed: "border-brand-500/35 bg-brand-500/10 text-brand-300",
  failed: "border-danger-500/40 bg-danger-500/10 text-danger-300",
  skipped: "border-surface-700 bg-surface-850 text-surface-400",
};

export const STATUS_DOTS: Record<string, string> = {
  queued: "bg-surface-500",
  running: "bg-info-400",
  completed: "bg-brand-400",
  failed: "bg-danger-400",
  skipped: "bg-surface-500",
};

export const STATUS_LABELS: Record<string, string> = {
  queued: "En attente",
  running: "En cours",
  completed: "Terminé",
  failed: "Échec",
  skipped: "Ignoré",
};
