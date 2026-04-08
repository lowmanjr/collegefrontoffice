import type { Metadata } from "next";
import { Inter, Oswald } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { BASE_URL } from "@/lib/constants";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const oswald = Oswald({
  variable: "--font-oswald",
  subsets: ["latin"],
  weight: ["400", "600", "700"],
});

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  alternates: {
    canonical: "/",
  },
  title: "College Front Office | NIL Valuations for College Sports",
  description:
    "The most comprehensive NIL valuation database in college sports. Proprietary player and team valuations for Power 4 college football.",
  openGraph: {
    title: "College Front Office | NIL Valuations for College Sports",
    description:
      "The most comprehensive NIL valuation database in college sports. Proprietary player and team valuations for Power 4 college football.",
    siteName: "CollegeFrontOffice",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "College Front Office | NIL Valuations for College Sports",
    description:
      "The most comprehensive NIL valuation database in college sports. Proprietary player and team valuations for Power 4 college football.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://a.espncdn.com" />
        <link rel="dns-prefetch" href="https://a.espncdn.com" />
      </head>
      <body
        className={`${inter.variable} ${oswald.variable} antialiased min-h-screen flex flex-col`}
        style={{ fontFamily: "var(--font-inter), sans-serif" }}
      >
        <Navbar />
        <main className="flex-grow">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
