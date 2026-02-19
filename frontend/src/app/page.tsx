import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="text-2xl font-bold text-primary">ListingAI</div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm font-medium text-gray-600 hover:text-primary"
            >
              Log In
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-gradient-to-br from-primary to-primary-dark px-6 py-24 text-white">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="mb-6 text-5xl font-bold leading-tight">
            AI-Powered Content for Every Listing
          </h1>
          <p className="mb-8 text-xl text-blue-100">
            Generate compelling listing descriptions, social media posts, email
            campaigns, flyer copy, and video scripts — all from your MLS data,
            in your brand voice.
          </p>
          <Link
            href="/register"
            className="inline-block rounded-lg bg-accent px-8 py-4 text-lg font-semibold text-primary-dark hover:bg-accent-light"
          >
            Start Free Trial
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="bg-white px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="mb-12 text-center text-3xl font-bold text-gray-900">
            One Platform, Six Content Types
          </h2>
          <div className="grid gap-8 md:grid-cols-3">
            {[
              {
                title: "Listing Descriptions",
                desc: "MLS-ready descriptions that highlight every feature.",
              },
              {
                title: "Social Media",
                desc: "Instagram, Facebook, LinkedIn, and X posts optimized for each platform.",
              },
              {
                title: "Email Campaigns",
                desc: "Just-listed, open house, and drip sequence emails.",
              },
              {
                title: "Flyer Copy",
                desc: "Print-ready headlines and body copy for flyers and postcards.",
              },
              {
                title: "Video Scripts",
                desc: "Walkthrough and promo video scripts with scene directions.",
              },
              {
                title: "Brand Voice",
                desc: "Every piece matches your brokerage's unique tone and style.",
              },
            ].map((feature) => (
              <div key={feature.title} className="rounded-lg border border-gray-200 p-6">
                <h3 className="mb-2 text-lg font-semibold text-gray-900">
                  {feature.title}
                </h3>
                <p className="text-gray-600">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-gray-50 px-6 py-8">
        <div className="mx-auto max-w-6xl text-center text-sm text-gray-500">
          &copy; {new Date().getFullYear()} ListingAI. Built for Broward County
          brokerages.
        </div>
      </footer>
    </div>
  );
}
