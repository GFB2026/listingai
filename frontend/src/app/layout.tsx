import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/lib/providers";

export const metadata: Metadata = {
  title: "ListingAI - AI-Powered Real Estate Content",
  description:
    "Generate listing descriptions, social media posts, email campaigns, and more from your MLS data.",
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
