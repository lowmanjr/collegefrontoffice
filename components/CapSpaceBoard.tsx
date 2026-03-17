import { supabase } from "@/lib/supabase";
import CapSpaceBoardClient, { type Team } from "@/components/CapSpaceBoardClient";

export default async function CapSpaceBoard() {
  const { data, error } = await supabase
    .from("teams")
    .select("id, university_name, conference, estimated_cap_space, active_payroll")
    .order("active_payroll", { ascending: false });

  if (error) {
    return (
      <p className="text-sm text-red-500">
        Failed to load teams: {error.message}
      </p>
    );
  }

  return <CapSpaceBoardClient initialTeams={data as Team[]} />;
}
