import type { Metadata } from "next";
import SportSubNav from "@/components/SportSubNav";

export const metadata: Metadata = {
  title: {
    template: "%s | CFO Football",
    default: "College Football NIL Valuations | CollegeFrontOffice",
  },
  description:
    "Proprietary NIL valuations for college football players and teams.",
};

export default function FootballLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <SportSubNav sport="football" />
      {children}
    </>
  );
}
