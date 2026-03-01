import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: {
    default: "Property Listings",
    template: "%s | Galt Ocean Realty",
  },
  description: "Browse luxury oceanfront properties and connect with a local real estate expert.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#1a365d",
};

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-surface">
      <main>{children}</main>
      <footer className="border-t border-gray-200 bg-white px-4 py-6 text-center text-xs text-gray-400">
        <p>Powered by ListingPulse</p>
      </footer>
    </div>
  );
}
