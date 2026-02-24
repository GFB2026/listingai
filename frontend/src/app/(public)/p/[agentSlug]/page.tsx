"use client";

import { use, useEffect, useState } from "react";
import publicApi from "@/lib/public-api";
import { captureUtmParams, getStoredUtm, getOrCreateSessionId } from "@/lib/utm";
import { formatPrice } from "@/lib/utils";
import { AgentHero } from "@/components/leads/AgentHero";
import { LeadCaptureForm } from "@/components/leads/LeadCaptureForm";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";

const TENANT_SLUG =
  process.env.NEXT_PUBLIC_TENANT_SLUG || "galt-ocean-realty";

interface AgentData {
  slug: string;
  name: string;
  headline: string | null;
  bio: string | null;
  photo_url: string | null;
  phone: string | null;
  email: string | null;
  theme: string | null;
}

interface BrokerageData {
  name: string;
  slug: string;
}

interface ListingData {
  id: string;
  address_full: string;
  price: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  sqft: number | null;
  photos: Array<{ url: string }> | null;
  property_type: string | null;
  status: string | null;
}

interface AgentPageResponse {
  agent: AgentData;
  brokerage: BrokerageData;
  listings: ListingData[];
}

export default function AgentLandingPage({
  params,
}: {
  params: Promise<{ agentSlug: string }>;
}) {
  const { agentSlug } = use(params);

  const [data, setData] = useState<AgentPageResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Capture UTM parameters from URL
    captureUtmParams();

    const sessionId = getOrCreateSessionId();
    const utm = getStoredUtm();

    // Fire visit tracking (non-blocking)
    publicApi
      .post("/visits", {
        tenant_slug: TENANT_SLUG,
        agent_slug: agentSlug,
        session_id: sessionId || null,
        utm_source: utm.utm_source ?? null,
        utm_medium: utm.utm_medium ?? null,
        utm_campaign: utm.utm_campaign ?? null,
        utm_content: utm.utm_content ?? null,
        utm_term: utm.utm_term ?? null,
        referrer_url: document.referrer || null,
        landing_url: window.location.href,
      })
      .catch(() => {
        // Visit tracking is best-effort; do not block the page
      });

    // Fetch agent page data
    publicApi
      .get<AgentPageResponse>(`/pages/${TENANT_SLUG}/${agentSlug}`)
      .then((res) => {
        setData(res.data);
      })
      .catch(() => {
        setError("Unable to load this page. Please try again later.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [agentSlug]);

  if (isLoading) {
    return <AgentPageSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center px-4">
        <p className="text-center text-gray-500">{error ?? "Page not found."}</p>
      </div>
    );
  }

  const { agent, brokerage, listings } = data;

  return (
    <div>
      {/* Agent hero */}
      <AgentHero
        name={agent.name}
        headline={agent.headline}
        bio={agent.bio}
        photoUrl={agent.photo_url}
        phone={agent.phone}
        email={agent.email}
        brokerageName={brokerage.name}
      />

      {/* Featured listings */}
      {listings.length > 0 && (
        <section className="px-4 py-8 md:py-12">
          <h2 className="mb-6 text-center text-lg font-bold text-primary md:text-xl">
            Featured Listings
          </h2>

          <div className="mx-auto grid max-w-5xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {listings.map((listing) => (
              <ListingCard
                key={listing.id}
                listing={listing}
                agentSlug={agentSlug}
              />
            ))}
          </div>
        </section>
      )}

      {/* Lead capture form */}
      <LeadCaptureForm
        tenantSlug={TENANT_SLUG}
        agentSlug={agentSlug}
        agentName={agent.name}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Inline listing card for the public page (links to listing detail)  */
/* ------------------------------------------------------------------ */

function ListingCard({
  listing,
  agentSlug,
}: {
  listing: ListingData;
  agentSlug: string;
}) {
  const photoUrl = listing.photos?.[0]?.url;

  return (
    <Link
      href={`/p/${agentSlug}/listing/${listing.id}`}
      className="group block overflow-hidden rounded-lg border border-gray-200 bg-white transition-shadow hover:shadow-md"
    >
      <div className="aspect-[16/10] bg-gray-100">
        {photoUrl ? (
          <img
            src={photoUrl}
            alt={listing.address_full}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-gray-300">
            No Photo
          </div>
        )}
      </div>

      <div className="p-4">
        <p className="text-lg font-bold text-primary">
          {listing.price != null ? formatPrice(listing.price) : "Price N/A"}
        </p>
        <p className="mt-0.5 text-sm text-gray-600 line-clamp-1">
          {listing.address_full}
        </p>
        <div className="mt-2 flex gap-3 text-xs text-gray-500">
          {listing.bedrooms != null && <span>{listing.bedrooms} bd</span>}
          {listing.bathrooms != null && <span>{listing.bathrooms} ba</span>}
          {listing.sqft != null && (
            <span>{listing.sqft.toLocaleString()} sqft</span>
          )}
        </div>
      </div>
    </Link>
  );
}

/* ------------------------------------------------------------------ */
/* Loading skeleton                                                    */
/* ------------------------------------------------------------------ */

function AgentPageSkeleton() {
  return (
    <div>
      {/* Agent hero skeleton */}
      <div className="flex flex-col items-center bg-white px-4 py-10">
        <Skeleton className="mb-4 h-32 w-32 rounded-full" />
        <Skeleton className="mb-2 h-7 w-48" />
        <Skeleton className="mb-2 h-5 w-64" />
        <Skeleton className="h-4 w-32" />
        <div className="mt-4 flex gap-4">
          <Skeleton className="h-10 w-36 rounded-full" />
          <Skeleton className="h-10 w-28 rounded-full" />
        </div>
      </div>

      {/* Listings grid skeleton */}
      <div className="px-4 py-8">
        <Skeleton className="mx-auto mb-6 h-6 w-40" />
        <div className="mx-auto grid max-w-5xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="overflow-hidden rounded-lg border border-gray-200 bg-white"
            >
              <Skeleton className="aspect-[16/10] w-full" />
              <div className="p-4">
                <Skeleton className="mb-2 h-5 w-3/4" />
                <Skeleton className="mb-2 h-4 w-full" />
                <div className="flex gap-3">
                  <Skeleton className="h-3 w-12" />
                  <Skeleton className="h-3 w-12" />
                  <Skeleton className="h-3 w-16" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
