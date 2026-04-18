export default function Loading() {
  return (
    <main className="min-h-screen bg-gray-100">
      <div className="bg-slate-900 text-white px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <div className="h-4 w-32 bg-slate-700 rounded mb-6" />
          <div className="h-10 w-80 bg-slate-700 rounded mb-3" />
          <div className="h-4 w-96 bg-slate-800 rounded" />
        </div>
      </div>
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="animate-pulse bg-white rounded-xl shadow-md p-4 space-y-3">
          <div className="h-10 rounded-md bg-slate-200" />
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="h-12 rounded-md bg-gray-100" />
          ))}
        </div>
      </div>
    </main>
  );
}
