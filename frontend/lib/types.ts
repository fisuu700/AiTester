export type Layer = "ui" | "api" | "db";
export type Severity = "info" | "warning" | "error";

export interface DBConfig {
  url: string;
}

export interface RunRequest {
  target_url: string;
  scenario: string;
  db?: DBConfig;
  max_steps?: number;
  headless?: boolean;
}

export interface UIAction {
  action: string;
  selector: string;
  value?: string | null;
  ok: boolean;
  error?: string | null;
  screenshot?: string | null;
  dom_preview: string;
}

export interface APIObservation {
  url: string;
  method: string;
  status: number;
  duration_ms: number;
  body?: Record<string, unknown> | null;
}

export interface DBVerification {
  query: string;
  rows: Record<string, unknown>[];
  row_count: number;
  ok: boolean;
  error?: string | null;
}

export interface Anomaly {
  layer: Layer;
  severity: Severity;
  message: string;
  details?: Record<string, unknown>;
}

export interface StepResult {
  index: number;
  title: string;
  ui: UIAction;
  api: APIObservation[];
  db?: DBVerification | null;
  anomalies: Anomaly[];
  root_cause?: string | null;
}

export interface RunReport {
  run_id: string;
  target_url: string;
  scenario: string;
  started_at: string;
  finished_at?: string | null;
  success: boolean;
  steps: StepResult[];
  anomalies: Anomaly[];
  root_cause?: string | null;
  summary: string;
}

export interface LogEvent {
  ts: string;
  level: string;
  layer?: Layer | null;
  message: string;
  data?: Record<string, unknown>;
}

export type WsMessage =
  | { type: "log"; event: LogEvent }
  | { type: "report"; report: RunReport }
  | { type: "error"; message: string };

// ---------------------------------------------------------------------------
// Plateforme : comptes, sites, scans
// ---------------------------------------------------------------------------

export interface User {
  id: number;
  email: string;
  created_at: string;
  api_key?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type ScanStatus = "queued" | "running" | "completed" | "failed";
export type AgentStatus = "pending" | "completed" | "failed" | "skipped";

export interface ScanSummary {
  id: string;
  status: ScanStatus;
  mode: "quick" | "full";
  global_score?: number | null;
  findings_count: number;
  critical_count: number;
  created_at: string;
  finished_at?: string | null;
}

export interface Site {
  id: number;
  url: string;
  name: string;
  verified: boolean;
  created_at: string;
  scans_count: number;
  last_scan?: ScanSummary | null;
}

export interface AgentResult {
  agent: string;
  status: AgentStatus;
  score: number;
  duration_ms: number;
  error?: string | null;
  metrics: Record<string, unknown>;
}

export interface Finding {
  id: number;
  agent: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  category: string;
  title: string;
  description: string;
  url: string;
  evidence: string;
  remediation: string;
}

export interface ScanDetail {
  id: string;
  site_id: number;
  site_url: string;
  site_name: string;
  status: ScanStatus;
  mode: "quick" | "full";
  scenario?: string | null;
  global_score?: number | null;
  reliability_score?: number | null;
  security_score?: number | null;
  performance_score?: number | null;
  accessibility_score?: number | null;
  functional_score?: number | null;
  summary: string;
  error?: string | null;
  triggered_by: string;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  agent_results: AgentResult[];
  findings: Finding[];
}

export interface HistoryPoint {
  scan_id: string;
  created_at: string;
  global_score?: number | null;
  reliability_score?: number | null;
  security_score?: number | null;
  performance_score?: number | null;
  accessibility_score?: number | null;
}

export interface Schedule {
  id: number;
  site_id: number;
  cron: string;
  mode: "quick" | "full";
  scenario?: string | null;
  enabled: boolean;
  last_run?: string | null;
}

export interface ServerEvent {
  type: string;
  ts?: string;
  [key: string]: unknown;
}
