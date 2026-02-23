"use client";

import { use } from "react";
import Link from "next/link";
import { formatPrice } from "@/lib/utils";
import { useListing, type Listing } from "@/hooks/useListings";

export default function ListingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const { data: listing, isLoading } = useListing(id);

  if (isLoading) {
    return <div className="py-12 text-center text-gray-400">Loading...</div>;
  }

  if (!listing) {
    return <div className="py-12 text-center text-gray-400">Listing not found</div>;
  }

  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {listing.address_full}
          </h1>
          <p className="text-lg text-primary font-semibold">
            {listing.price ? formatPrice(listing.price) : "Price N/A"}
          </p>
        </div>
        <Link
          href={`/listings/${id}/content`}
          className="rounded-lg bg-primary px-6 py-2.5 font-medium text-white hover:bg-primary-light"
        >
          Generate Content
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Property Details */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">Details</h2>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-gray-500">Type</dt>
              <dd className="font-medium text-gray-900">{listing.property_type || "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Status</dt>
              <dd className="font-medium text-gray-900">{listing.status || "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Bedrooms</dt>
              <dd className="font-medium text-gray-900">{listing.bedrooms ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Bathrooms</dt>
              <dd className="font-medium text-gray-900">{listing.bathrooms ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Sqft</dt>
              <dd className="font-medium text-gray-900">
                {listing.sqft ? listing.sqft.toLocaleString() : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Year Built</dt>
              <dd className="font-medium text-gray-900">{listing.year_built ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">MLS #</dt>
              <dd className="font-medium text-gray-900">{listing.mls_listing_id || "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Agent</dt>
              <dd className="font-medium text-gray-900">
                {listing.listing_agent_name || "—"}
              </dd>
            </div>
          </dl>
        </div>

        {/* Features */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">Features</h2>
          {listing.features?.length ? (
            <div className="flex flex-wrap gap-2">
              {listing.features.map((f: string, i: number) => (
                <span
                  key={i}
                  className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
                >
                  {f}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">No features listed</p>
          )}
        </div>
      </div>

      {/* Photo Gallery */}
      {listing.photos?.length > 0 && (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">Photos</h2>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {listing.photos.map((photo, i) => {
              const src = photo.url;
              if (!src) return null;
              return (
                <img
                  key={i}
                  src={src}
                  alt={`Listing photo ${i + 1}`}
                  className="h-48 w-64 flex-shrink-0 rounded-lg object-cover"
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Original Description */}
      {listing.description_original && (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            Original MLS Description
          </h2>
          <p className="text-sm leading-relaxed text-gray-700">
            {listing.description_original}
          </p>
        </div>
      )}
    </div>
  );
}
