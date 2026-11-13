"use client";

import type {
  AuthResponse,
  HistoryPoint,
  ScanDetail,
  ScanSummary,
  Schedule,
  Site,
  User,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? "https://aitester-jgnla.fly.dev"
    : "http://localhost:8000");
const TOKEN_KEY = "ai-tester-token";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    if (response.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth")) {
      setToken(null);
      window.location.href = "/login";
    }
    throw new ApiError(String(detail), response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

// --- Auth ------------------------------------------------------------------

export const authApi = {
  register: (email: string, password: string) =>
    api<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    api<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => api<User>("/api/auth/me"),
  createApiKey: () => api<User>("/api/auth/api-key", { method: "POST" }),
  revokeApiKey: () => api<User>("/api/auth/api-key", { method: "DELETE" }),
};

// --- Sites -----------------------------------------------------------------

export const sitesApi = {
  list: () => api<Site[]>("/api/sites"),
  get: (id: number | string) => api<Site>(`/api/sites/${id}`),
  create: (url: string, name: string, consent: boolean) =>
    api<Site>("/api/sites", {
      method: "POST",
      body: JSON.stringify({ url, name, consent }),
    }),
  remove: (id: number) => api<void>(`/api/sites/${id}`, { method: "DELETE" }),
  history: (id: number | string) => api<HistoryPoint[]>(`/api/sites/${id}/history`),
  launchScan: (id: number | string, mode: "quick" | "full", scenario?: string) =>
    api<ScanSummary>(`/api/sites/${id}/scans`, {
      method: "POST",
      body: JSON.stringify({ mode, scenario: scenario || null }),
    }),
  schedules: (id: number | string) => api<Schedule[]>(`/api/sites/${id}/schedules`),
  upsertSchedule: (id: number | string, cron: string, mode: "quick" | "full") =>
    api<Schedule>(`/api/sites/${id}/schedule`, {
      method: "POST",
      body: JSON.stringify({ cron, mode, enabled: true }),
    }),
  deleteSchedule: (scheduleId: number) =>
    api<void>(`/api/sites/schedules/${scheduleId}`, { method: "DELETE" }),
};

// --- Scans -----------------------------------------------------------------

export const scansApi = {
  list: (limit = 20) => api<ScanSummary[]>(`/api/scans?limit=${limit}`),
  get: (id: string) => api<ScanDetail>(`/api/scans/${id}`),
  remove: (id: string) => api<void>(`/api/scans/${id}`, { method: "DELETE" }),
};

export async function downloadReport(scanId: string, format: "json" | "html" | "pdf"): Promise<void> {
  const response = await fetch(`${API_URL}/api/scans/${scanId}/report?format=${format}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new ApiError("Export impossible", response.status);

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `rapport_${scanId}.${format}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function wsUrl(path: string): string {
  const base = API_URL.replace(/^https?:\/\//, "");
  const protocol = API_URL.startsWith("https") ? "wss" : "ws";
  return `${protocol}://${base}${path}`;
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const iso = /[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

export function timeAgo(value?: string | null): string {
  if (!value) return "jamais";
  const iso = /[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  const days = Math.round(hours / 24);
  return `il y a ${days} j`;
}
