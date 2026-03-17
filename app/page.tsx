import CapSpaceBoard from "@/components/CapSpaceBoard";
import PlayerTable from "@/components/PlayerTable";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-100 px-4 py-12">
      <div className="mx-auto max-w-5xl space-y-10">
        <h1 className="text-4xl font-bold text-gray-900">
          CollegeFrontOffice.com
        </h1>

        {/* Cap Space Dashboard */}
        <section>
          <h2 className="mb-4 text-xl font-semibold text-gray-700">
            Team Cap Space
          </h2>
          <CapSpaceBoard />
        </section>

        {/* Player Valuations Table */}
        <section>
          <PlayerTable />
        </section>
      </div>
    </main>
  );
}
