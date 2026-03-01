import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { initSentry } from "@/lib/sentry";

initSentry();

export const metadata: Metadata = {
  title: {
    default: "ListingPulse - AI-Powered Real Estate Content",
    template: "%s | ListingPulse",
  },
  description:
    "Generate listing descriptions, social media posts, email campaigns, and more from your MLS data.",
  robots: { index: false, follow: false },
  icons: { icon: "/favicon.ico" },
};

export const viewport: Viewport = {
  themeColor: "#1a365d",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
