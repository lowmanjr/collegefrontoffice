import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-10">
          <p
            className="text-8xl font-bold text-slate-200 leading-none mb-2"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            404
          </p>

          <h1
            className="text-2xl font-bold text-slate-900 mb-3 uppercase"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Page Not Found
          </h1>
          <p className="text-sm text-slate-500 mb-8 leading-relaxed">
            The page you&apos;re looking for doesn&apos;t exist or may have been moved.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/"
              className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              ← Back to Dashboard
            </Link>
            <Link
              href="/football/players"
              className="rounded-lg border border-gray-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-gray-50 transition-colors"
            >
              Browse Players
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
