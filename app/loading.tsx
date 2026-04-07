export default function Loading() {
  return (
    <section className="bg-slate-900 py-14 pb-16 px-4">
      <div className="mx-auto max-w-4xl text-center">
        <div className="h-10 w-80 bg-slate-700 rounded mx-auto mb-3" />
        <div className="h-5 w-96 bg-slate-800 rounded mx-auto mb-6" />
        <div className="h-12 w-full max-w-xl bg-slate-800 rounded-xl mx-auto mb-12" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="animate-pulse h-20 rounded-xl bg-slate-800/50 border border-slate-700" />
          ))}
        </div>      </div>
    </section>
  );
}
