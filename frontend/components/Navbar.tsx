"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/lib/auth";

const LINKS = [
  { href: "/", label: "Tableau de bord" },
  { href: "/scans", label: "Scans" },
  { href: "/account", label: "Compte" },
];

export default function Navbar() {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  if (loading || !user) return null;

  const handleLogout = () => {
    logout();
    router.replace("/login");
    setUserMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 border-b border-surface-800 bg-surface-950/90 backdrop-blur-md">
      <nav className="container-app" aria-label="Navigation principale">
        <div className="flex h-14 items-center justify-between gap-6">
          <Link
            href="/"
            className="flex shrink-0 items-center gap-2.5"
            aria-label="AI Tester - Accueil"
          >
            <span
              className="flex h-7 w-7 items-center justify-center rounded-[5px] border border-brand-500/40 bg-brand-500/10 font-mono text-[11px] font-semibold leading-none text-brand-300"
              aria-hidden="true"
            >
              AT
            </span>
            <span className="text-body-md font-semibold tracking-tight text-surface-50">
              AI Tester
            </span>
            <span className="hidden rounded border border-surface-700 px-1 py-px font-mono text-[10px] uppercase tracking-wider text-surface-500 sm:inline">
              v2
            </span>
          </Link>

          <div className="hidden h-full items-center gap-1 md:flex">
            {LINKS.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`relative flex h-14 items-center px-3 text-body-sm transition-colors ${
                    active
                      ? "text-surface-50"
                      : "text-surface-400 hover:text-surface-100"
                  }`}
                  aria-current={active ? "page" : undefined}
                >
                  {link.label}
                  {active && (
                    <span
                      className="absolute inset-x-2.5 bottom-0 h-px bg-brand-400"
                      aria-hidden="true"
                    />
                  )}
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-1.5">
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 rounded-md px-1.5 py-1 text-body-sm text-surface-400 transition-colors hover:bg-surface-850 hover:text-surface-100"
                aria-expanded={userMenuOpen}
                aria-haspopup="true"
                aria-label="Menu utilisateur"
              >
                <span className="hidden max-w-[150px] truncate sm:block">{user.email}</span>
                <span className="flex h-6 w-6 items-center justify-center rounded-[5px] border border-surface-700 bg-surface-850 font-mono text-[11px] font-medium text-surface-200">
                  {user.email.charAt(0).toUpperCase()}
                </span>
                <svg
                  className={`h-3.5 w-3.5 text-surface-500 transition-transform ${userMenuOpen ? "rotate-180" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {userMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setUserMenuOpen(false)}
                    aria-hidden="true"
                  />
                  <div className="dropdown">
                    <div className="border-b border-surface-800 px-3 py-2">
                      <p className="eyebrow">Session</p>
                      <p className="mt-0.5 truncate text-body-xs text-surface-300">{user.email}</p>
                    </div>
                    <div className="p-1">
                      <Link
                        href="/account"
                        className="dropdown-item rounded"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        <svg className="h-4 w-4 text-surface-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        Mon compte
                      </Link>
                      <button
                        onClick={handleLogout}
                        className="dropdown-item rounded text-danger-300 hover:bg-danger-500/10 hover:text-danger-300"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        Déconnexion
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="rounded-md p-1.5 text-surface-400 transition-colors hover:bg-surface-850 hover:text-surface-100 md:hidden"
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-menu"
              aria-label="Ouvrir le menu"
            >
              {mobileMenuOpen ? (
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7h16M4 12h16M4 17h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div id="mobile-menu" className="border-t border-surface-800 pb-3 pt-2 md:hidden">
            <div className="flex flex-col">
              {LINKS.map((link) => {
                const active = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`rounded-md px-2.5 py-2 text-body-sm transition-colors ${
                      active
                        ? "bg-surface-850 text-surface-50"
                        : "text-surface-400 hover:bg-surface-850 hover:text-surface-100"
                    }`}
                    aria-current={active ? "page" : undefined}
                  >
                    {link.label}
                  </Link>
                );
              })}
              <button
                onClick={handleLogout}
                className="mt-1 flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-body-sm text-danger-300 transition-colors hover:bg-danger-500/10"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Déconnexion
              </button>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
