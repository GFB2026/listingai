"use client";

import { use, useEffect, useState } from "react";
import publicApi from "@/lib/public-api";
import { captureUtmParams, getStoredUtm, getOrCreateSessionId } from "@/lib/utm";
import { AgentHero } from "@/components/leads/AgentHero";
import { PropertyHero } from "@/components/leads/PropertyHero";
import { LeadCaptureForm } from "@/components/leads/LeadCaptureForm";
import { Skeleton } from "@/components/ui/skeleton";

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

interface ListingDetail {
  id: string;
  address_full: string;
  address_city: string | null;
  address_state: string | null;
  price: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  sqft: number | null;
  lot_sqft: number | null;
  year_built: number | null;
  description_original: string | null;
  features: string[] | null;
  photos: Array<{ url: string }> | null;
  property_type: string | null;
  status: string | null;
}

interface ListingPageResponse {
  agent: AgentData;
  brokerage: BrokerageData;
  listing: ListingDetail;
}

export default function ListingLandingPage({
  params,
}: {
  params: Promise<{ agentSlug: string; listingId: string }>;
}) {
  const { agentSlug, listingId } = use(params);

  const [data, setData] = useState<ListingPageResponse | null>(null);
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
        listing_id: listingId,
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

    // Fetch listing page data
    publicApi
      .get<ListingPageResponse>(
        `/pages/${TENANT_SLUG}/${agentSlug}/listings/${listingId}`
      )
      .then((res) => {
        setData(res.data);
      })
      .catch(() => {
        setError("Unable to load this listing. Please try again later.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [agentSlug, listingId]);

  if (isLoading) {
    return <ListingPageSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center px-4">
        <p className="text-center text-gray-500">
          {error ?? "Listing not found."}
        </p>
      </div>
    );
  }

  const { agent, brokerage, listing } = data;

  return (
    <div>
      {/* Property hero */}
      <PropertyHero listing={listing} />

      {/* Agent hero (compact) */}
      <AgentHero
        name={agent.name}
        headline={agent.headline}
        bio={agent.bio}
        photoUrl={agent.photo_url}
        phone={agent.phone}
        email={agent.email}
        brokerageName={brokerage.name}
        compact
      />

      {/* Lead capture form — pre-filled with listing address */}
      <LeadCaptureForm
        tenantSlug={TENANT_SLUG}
        agentSlug={agentSlug}
        listingId={listingId}
        propertyInterest={listing.address_full}
        agentName={agent.name}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Loading skeleton                                                    */
/* ------------------------------------------------------------------ */

function ListingPageSkeleton() {
  return (
    <div>
      {/* Property hero skeleton */}
      <div className="bg-white">
        <Skeleton className="aspect-[16/9] w-full md:aspect-[21/9]" />
        <div className="mx-auto max-w-3xl px-4 py-6">
          <Skeleton className="mb-2 h-8 w-48" />
          <Skeleton className="mb-4 h-5 w-72" />
          <div className="flex gap-4">
            <Skeleton className="h-14 w-20 rounded-lg" />
            <Skeleton className="h-14 w-20 rounded-lg" />
            <Skeleton className="h-14 w-20 rounded-lg" />
            <Skeleton className="h-14 w-24 rounded-lg" />
          </div>
          <Skeleton className="mt-6 h-4 w-24" />
          <Skeleton className="mt-2 h-20 w-full" />
        </div>
      </div>

      {/* Agent hero skeleton (compact) */}
      <div className="flex flex-col items-center bg-white px-4 py-6">
        <Skeleton className="mb-4 h-24 w-24 rounded-full" />
        <Skeleton className="mb-2 h-6 w-40" />
        <Skeleton className="h-4 w-56" />
      </div>
    </div>
  );
}
