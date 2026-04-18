"use server";

import { revalidatePath } from "next/cache";
import { createSupabaseServerClient } from "@/lib/supabase-server";
import { supabaseAdmin } from "@/lib/supabase-admin";
import { proposalSchema } from "@/lib/validators";
import type { ValidatedProposal } from "@/lib/validators";

// ── Types ────────────────────────────────────────────────────────────────────

export interface ActionResult {
  success: boolean;
  error?: string;
}

// ── Auth helper ──────────────────────────────────────────────────────────────

async function requireAuth(): Promise<void> {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("Unauthorized");
}

// ── Actions ──────────────────────────────────────────────────────────────────

export async function rejectProposal(proposalId: string): Promise<ActionResult> {
  try {
    await requireAuth();

    const { error } = await supabaseAdmin
      .from("proposed_events")
      .update({ status: "rejected" })
      .eq("id", proposalId);

    if (error) throw new Error(error.message);

    revalidatePath("/admin");
    return { success: true };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("[rejectProposal]", message);
    return { success: false, error: message };
  }
}

export async function approveProposal(input: unknown): Promise<ActionResult> {
  // ── 1. Validate input ──────────────────────────────────────────────────────
  const parsed = proposalSchema.safeParse(input);
  if (!parsed.success) {
    const message = parsed.error.issues.map((e: { message: string }) => e.message).join("; ");
    console.error("[approveProposal] Validation failed:", message);
    return { success: false, error: `Invalid proposal data: ${message}` };
  }

  const proposal: ValidatedProposal = parsed.data;

  try {
    await requireAuth();

    // ── 2. Mark proposal approved (Step A) ────────────────────────────────────
    const { error: approveError } = await supabaseAdmin
      .from("proposed_events")
      .update({ status: "approved" })
      .eq("id", proposal.id);

    if (approveError) {
      throw new Error(`Failed to approve proposal: ${approveError.message}`);
    }

    // ── 3. Insert into live player_events timeline (Step B) ───────────────────
    const { error: insertError } = await supabaseAdmin.from("player_events").insert({
      player_id: proposal.player_id,
      event_type: proposal.event_type,
      event_date: proposal.event_date,
      new_valuation: proposal.proposed_valuation,
      previous_valuation: proposal.current_valuation,
      reported_deal: proposal.reported_deal,
      description: proposal.description,
    });

    if (insertError) {
      // Rollback Step A
      await supabaseAdmin
        .from("proposed_events")
        .update({ status: "pending" })
        .eq("id", proposal.id);
      throw new Error(`Failed to insert event: ${insertError.message}`);
    }

    // ── 4. Update player's live cfo_valuation (Step C) ────────────────────────
    const { error: updateError } = await supabaseAdmin
      .from("players")
      .update({
        cfo_valuation: proposal.proposed_valuation,
        last_updated: new Date().toISOString(),
      })
      .eq("id", proposal.player_id);

    if (updateError) {
      // Rollback Steps A + B: revert proposal status and delete the inserted event
      await Promise.all([
        supabaseAdmin.from("proposed_events").update({ status: "pending" }).eq("id", proposal.id),
        supabaseAdmin
          .from("player_events")
          .delete()
          .eq("player_id", proposal.player_id)
          .eq("event_date", proposal.event_date)
          .eq("event_type", proposal.event_type),
      ]);
      throw new Error(`Failed to update player valuation: ${updateError.message}`);
    }

    revalidatePath("/admin");
    revalidatePath(`/football/players/${proposal.player_id}`);
    return { success: true };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("[approveProposal]", message);
    return { success: false, error: message };
  }
}
