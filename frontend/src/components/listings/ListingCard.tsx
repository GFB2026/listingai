"use client";

import Link from "next/link";
import { formatPrice } from "@/lib/utils";

interface ListingCardProps {
  listing: {
    id: string;
    address_full: string;
    price: number | null;
    bedrooms: number | null;
    bathrooms: number | null;
    sqft: number | null;
    property_type: string | null;
    status: string | null;
    photos: Array<{ url: string }> | null;
  };
}

export function ListingCard({ listing }: ListingCardProps) {
  const photoUrl = listing.photos?.[0]?.url;

  return (
    <Link
      href={`/listings/${listing.id}`}
      className="group block overflow-hidden rounded-lg border border-gray-200 bg-white transition-shadow hover:shadow-md"
    >
      {/* Photo */}
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

      {/* Details */}
      <div className="p-4">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-lg font-bold text-primary">
            {listing.price ? formatPrice(listing.price) : "Price N/A"}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              listing.status === "active"
                ? "bg-green-100 text-green-700"
                : listing.status === "pending"
                  ? "bg-yellow-100 text-yellow-700"
                  : listing.status === "sold"
                    ? "bg-red-100 text-red-700"
                    : "bg-gray-100 text-gray-600"
            }`}
          >
            {listing.status || "unknown"}
          </span>
        </div>

        <p className="mb-2 text-sm text-gray-600 line-clamp-1">
          {listing.address_full}
        </p>

        <div className="flex gap-3 text-xs text-gray-500">
          {listing.bedrooms != null && <span>{listing.bedrooms} bd</span>}
          {listing.bathrooms != null && <span>{listing.bathrooms} ba</span>}
          {listing.sqft != null && (
            <span>{listing.sqft.toLocaleString()} sqft</span>
          )}
          {listing.property_type && <span>{listing.property_type}</span>}
        </div>
      </div>
    </Link>
  );
}
