"use client";

import { ListingCard } from "./ListingCard";

interface Props {
  listings: any[];
  total: number;
  page: number;
  onPageChange: (page: number) => void;
}

export function ListingGrid({ listings, total, page, onPageChange }: Props) {
  const pageSize = 20;
  const totalPages = Math.ceil(total / pageSize);

  if (!listings.length) {
    return (
      <div className="py-12 text-center">
        <p className="text-gray-400">
          No listings found. Sync your MLS or create a listing manually.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {listings.map((listing) => (
          <ListingCard key={listing.id} listing={listing} />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-2">
          <button
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page === 1}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
