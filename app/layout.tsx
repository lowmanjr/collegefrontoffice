import type { Metadata } from "next";
import { Inter, Oswald } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

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
  title: "CollegeFrontOffice | Mapping the College Sports Economy",
  description:
    "Proprietary estimates, player valuations, and team cap space projections for the modern NIL era.",
  openGraph: {
    title: "CollegeFrontOffice | Mapping the College Sports Economy",
    description:
      "Proprietary estimates, player valuations, and team cap space projections for the modern NIL era.",
    siteName: "CollegeFrontOffice",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "CollegeFrontOffice | Mapping the College Sports Economy",
    description:
      "Proprietary estimates, player valuations, and team cap space projections for the modern NIL era.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${oswald.variable} antialiased min-h-screen flex flex-col`}
        style={{ fontFamily: "var(--font-inter), sans-serif" }}
      >
        <Navbar />
        <main className="flex-grow">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
