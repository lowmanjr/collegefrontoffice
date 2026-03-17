import { Card } from "@tremor/react";
import { supabase } from "@/lib/supabase";
import PlayerTableClient, { type Player } from "@/components/PlayerTableClient";

export default async function PlayerTable() {
  const { data, error } = await supabase
    .from("players")
    .select("id, name, position, star_rating, experience_level, cfo_valuation")
    .order("cfo_valuation", { ascending: false });

  if (error) {
    return (
      <Card>
        <p className="text-sm text-red-500">
          Failed to load players: {error.message}
        </p>
      </Card>
    );
  }

  return <PlayerTableClient initialPlayers={data as Player[]} />;
}
