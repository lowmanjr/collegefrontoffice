"use client";

import { useEffect } from "react";
import Link from "next/link";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: ErrorProps) {
  useEffect(() => {
    // Log to an error reporting service in the future
    console.error(error);
  }, [error]);

  return (
    <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-10">
          {/* Icon */}
          <div className="mx-auto mb-6 h-14 w-14 rounded-full bg-red-50 flex items-center justify-center">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
                stroke="#dc2626"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>

          <h1
            className="text-3xl font-bold text-slate-900 mb-2 uppercase"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Something went wrong
          </h1>
          <p className="text-sm text-slate-500 mb-8 leading-relaxed">
            An unexpected error occurred. Our team has been notified.
            {error.digest && (
              <span className="block mt-1 font-mono text-xs text-slate-400">
                Error ID: {error.digest}
              </span>
            )}
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={reset}
              className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Try Again
            </button>
            <Link
              href="/"
              className="rounded-lg border border-gray-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-gray-50 transition-colors"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
