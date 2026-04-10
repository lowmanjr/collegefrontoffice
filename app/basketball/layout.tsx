import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    template: "%s | CFO Basketball",
    default: "College Basketball NIL Valuations | CollegeFrontOffice",
  },
  description:
    "AI-powered NIL valuations for college basketball players.",
};

export default function BasketballLayout({ children }: { children: React.ReactNode }) {
  return children;
}
