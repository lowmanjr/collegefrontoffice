"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { createSupabaseBrowserClient } from "@/lib/supabase-browser";

// ── Inner form — uses useSearchParams, must be inside <Suspense> ─────────────

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get("redirect") ?? "/admin";
  const callbackErr = searchParams.get("error");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(
    callbackErr ? "Authentication failed. Please try again." : null
  );
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    const supabase = createSupabaseBrowserClient();
    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (authError) {
      setError(authError.message);
      setIsLoading(false);
      return;
    }

    // Refresh server-component cache so layout auth checks re-run.
    router.refresh();
    router.push(redirectTo);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="email"
          className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1.5"
        >
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-400 focus:bg-white focus:outline-none transition-colors"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label
          htmlFor="password"
          className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1.5"
        >
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-slate-400 focus:bg-white focus:outline-none transition-colors"
          placeholder="••••••••"
        />
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-100 px-3 py-2.5">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        style={{ fontFamily: "var(--font-oswald), sans-serif" }}
      >
        {isLoading ? "Signing in…" : "Sign In"}
      </button>
    </form>
  );
}

// ── Page shell ───────────────────────────────────────────────────────────────

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="mb-8 text-center">
          <Link href="/" className="inline-flex items-center gap-2 group">
            <svg
              width="38"
              height="32"
              viewBox="0 0 38 32"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <text
                x="1"
                y="26"
                fontFamily="var(--font-oswald), sans-serif"
                fontStyle="italic"
                fontWeight="700"
                fontSize="26"
                fill="#1e293b"
                letterSpacing="-1"
              >
                CFO
              </text>
              <line
                x1="33"
                y1="2"
                x2="27"
                y2="30"
                stroke="#4ade80"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
            <span
              className="text-sm font-semibold text-slate-700 group-hover:text-slate-900 transition-colors"
              style={{ fontFamily: "var(--font-oswald), sans-serif", letterSpacing: "0.06em" }}
            >
              CollegeFrontOffice
            </span>
          </Link>
          <p className="mt-3 text-xs uppercase tracking-widest text-slate-400">Admin Access</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-8">
          <h1
            className="text-xl font-bold text-slate-900 mb-6"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Sign In
          </h1>

          {/* Suspense boundary required by useSearchParams */}
          <Suspense fallback={<div className="h-48 animate-pulse rounded-lg bg-gray-100" />}>
            <LoginForm />
          </Suspense>
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          <Link href="/" className="hover:text-slate-600 transition-colors">
            ← Back to CollegeFrontOffice.com
          </Link>
        </p>
      </div>
    </main>
  );
}
