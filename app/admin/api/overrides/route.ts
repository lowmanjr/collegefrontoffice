import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase-admin";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { player_id, total_value, years, source_name, source_url } = body;

    if (!player_id || !total_value || !years || !source_name) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }

    // Get the player name for the override row
    const { data: player } = await supabaseAdmin
      .from("players")
      .select("name")
      .eq("id", player_id)
      .single();

    const playerName = player?.name ?? "";

    // Insert the override
    const { error: insertError } = await supabaseAdmin
      .from("nil_overrides")
      .insert({
        player_id,
        name: playerName,
        total_value: Math.round(total_value),
        years: parseFloat(String(years)),
        source_name,
        source_url: source_url || null,
      });

    if (insertError) {
      return NextResponse.json({ error: insertError.message }, { status: 500 });
    }

    // Set is_override = true on the player
    const { error: playerError } = await supabaseAdmin
      .from("players")
      .update({ is_override: true })
      .eq("id", player_id);

    if (playerError) {
      return NextResponse.json({ error: playerError.message }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const playerId = searchParams.get("player_id");

  if (!playerId) {
    return NextResponse.json({ error: "Missing player_id" }, { status: 400 });
  }

  // Delete all overrides for this player
  const { error: deleteError } = await supabaseAdmin
    .from("nil_overrides")
    .delete()
    .eq("player_id", playerId);

  if (deleteError) {
    return NextResponse.json({ error: deleteError.message }, { status: 500 });
  }

  // Set is_override = false on the player
  const { error: playerError } = await supabaseAdmin
    .from("players")
    .update({ is_override: false })
    .eq("id", playerId);

  if (playerError) {
    return NextResponse.json({ error: playerError.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
