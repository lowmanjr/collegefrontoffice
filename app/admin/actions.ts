"use server";

import { supabase } from "@/lib/supabase";
import { revalidatePath } from "next/cache";

export async function rejectProposal(proposalId: string) {
  await supabase
    .from("proposed_events")
    .update({ status: "rejected" })
    .eq("id", proposalId);

  revalidatePath("/admin");
}

export async function approveProposal(proposal: {
  id: string;
  player_id: string;
  event_type: string;
  event_date: string;
  proposed_valuation: number;
  current_valuation: number | null;
  reported_deal: number | null;
  description: string | null;
}) {
  // 1. Mark proposal approved
  await supabase
    .from("proposed_events")
    .update({ status: "approved" })
    .eq("id", proposal.id);

  // 2. Insert into live player_events timeline
  await supabase.from("player_events").insert({
    player_id:          proposal.player_id,
    event_type:         proposal.event_type,
    event_date:         proposal.event_date,
    new_valuation:      proposal.proposed_valuation,
    previous_valuation: proposal.current_valuation,
    reported_deal:      proposal.reported_deal,
    description:        proposal.description,
  });

  // 3. Update player's live cfo_valuation
  await supabase
    .from("players")
    .update({ cfo_valuation: proposal.proposed_valuation })
    .eq("id", proposal.player_id);

  revalidatePath("/admin");
  revalidatePath(`/players/${proposal.player_id}`);
}
