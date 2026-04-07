import { z } from "zod";

export const proposalSchema = z.object({
  id: z.string().uuid(),
  player_id: z.string().uuid(),
  event_type: z.string().min(1).max(100),
  event_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Must be YYYY-MM-DD"),
  proposed_valuation: z.number().int().min(0).max(100_000_000),
  current_valuation: z.number().int().min(0).nullable(),
  reported_deal: z.number().int().min(0).nullable(),
  description: z.string().max(2000).nullable(),
});

export type ValidatedProposal = z.infer<typeof proposalSchema>;
