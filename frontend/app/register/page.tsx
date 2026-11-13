"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const validateEmail = (value: string) => {
    if (!value.trim()) return "L'email est requis";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())) return "Format d'email invalide";
    return null;
  };

  const validatePassword = (value: string) => {
    if (!value) return "Le mot de passe est requis";
    if (value.length < 8) return "Minimum 8 caractères";
    return null;
  };

  const validateConfirm = (value: string) => {
    if (!value) return "Veuillez confirmer le mot de passe";
    if (value !== password) return "Les mots de passe ne correspondent pas";
    return null;
  };

  const handleEmailChange = (value: string) => {
    setEmail(value);
    setEmailError(validateEmail(value));
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    setPasswordError(validatePassword(value));
    if (confirm) setConfirmError(validateConfirm(value));
  };

  const handleConfirmChange = (value: string) => {
    setConfirm(value);
    setConfirmError(validateConfirm(value));
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const emailErr = validateEmail(email);
    const passwordErr = validatePassword(password);
    const confirmErr = validateConfirm(confirm);
    if (emailErr || passwordErr || confirmErr) return;

    setBusy(true);
    setError(null);
    try {
      await register(email.trim(), password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Inscription impossible.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col">
      <div className="container-app flex flex-1 items-center justify-center py-14">
        <div className="w-full max-w-[400px]">
          <Link href="/" className="mb-10 inline-flex items-center gap-2.5">
            <span
              className="flex h-7 w-7 items-center justify-center rounded-[5px] border border-brand-500/40 bg-brand-500/10 font-mono text-[11px] font-semibold leading-none text-brand-300"
              aria-hidden="true"
            >
              AT
            </span>
            <span className="text-body-md font-semibold tracking-tight text-surface-50">AI Tester</span>
          </Link>

          <p className="eyebrow">Nouveau compte</p>
          <h1 className="mt-1.5 text-heading-lg font-semibold">Créer un compte</h1>
          <p className="mt-1.5 text-body-sm text-surface-500">
            Ajoutez vos sites et lancez vos premiers scans.
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="label">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => handleEmailChange(e.target.value)}
                required
                disabled={busy}
                autoComplete="email"
                className={`input ${emailError ? "input-error" : ""}`}
                aria-describedby={emailError ? "email-error" : undefined}
                aria-invalid={!!emailError}
                placeholder="vous@exemple.com"
              />
              {emailError && (
                <p id="email-error" className="mt-1.5 text-[11px] text-danger-300" role="alert">
                  {emailError}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="label">
                Mot de passe <span className="font-normal text-surface-600">· 8 caractères min.</span>
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => handlePasswordChange(e.target.value)}
                required
                disabled={busy}
                autoComplete="new-password"
                className={`input ${passwordError ? "input-error" : ""}`}
                aria-describedby={passwordError ? "password-error" : undefined}
                aria-invalid={!!passwordError}
                placeholder="••••••••"
                minLength={8}
              />
              {passwordError && (
                <p id="password-error" className="mt-1.5 text-[11px] text-danger-300" role="alert">
                  {passwordError}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="confirm" className="label">Confirmation</label>
              <input
                id="confirm"
                type="password"
                value={confirm}
                onChange={(e) => handleConfirmChange(e.target.value)}
                required
                disabled={busy}
                autoComplete="new-password"
                className={`input ${confirmError ? "input-error" : ""}`}
                aria-describedby={confirmError ? "confirm-error" : undefined}
                aria-invalid={!!confirmError}
                placeholder="••••••••"
                minLength={8}
              />
              {confirmError && (
                <p id="confirm-error" className="mt-1.5 text-[11px] text-danger-300" role="alert">
                  {confirmError}
                </p>
              )}
            </div>

            {error && (
              <p
                className="rounded-md border border-danger-500/30 bg-danger-500/5 px-3 py-2 text-body-xs text-danger-300 animate-fade-in"
                role="alert"
              >
                {error}
              </p>
            )}

            <button type="submit" disabled={busy} className="btn-primary btn-lg w-full">
              {busy ? (
                <>
                  <svg className="h-4 w-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Création…
                </>
              ) : (
                "Créer mon compte"
              )}
            </button>
          </form>

          <div className="mt-7 border-t border-surface-800 pt-5">
            <p className="text-body-xs text-surface-500">
              Déjà inscrit ?{" "}
              <Link href="/login" className="link">
                Se connecter
              </Link>
            </p>
          </div>
        </div>
      </div>

      <footer className="border-t border-surface-800/70">
        <div className="container-app flex flex-wrap items-center justify-between gap-2 py-4 text-[11px] text-surface-600">
          <span>Plateforme de test automatisé</span>
          <span className="font-mono uppercase tracking-[0.14em]">
            Fiabilité · Sécurité · Performance · Accessibilité
          </span>
        </div>
      </footer>
    </main>
  );
}
