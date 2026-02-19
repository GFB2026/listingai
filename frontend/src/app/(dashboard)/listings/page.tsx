"use client";

import { useState } from "react";
import { useListings } from "@/hooks/useListings";
import { ListingGrid } from "@/components/listings/ListingGrid";
import { ListingFilters } from "@/components/listings/ListingFilters";
import api from "@/lib/api";

export default function ListingsPage() {
  const [filters, setFilters] = useState({
    status: "",
    property_type: "",
    city: "",
    page: 1,
  });

  const { data, isLoading } = useListings(filters);

  const triggerSync = async () => {
    await api.post("/listings/sync");
    alert("MLS sync triggered. Listings will update shortly.");
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Listings</h1>
          <p className="text-sm text-gray-500">
            {data?.total ?? 0} listings synced from MLS
          </p>
        </div>
        <button
          onClick={triggerSync}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light"
        >
          Sync MLS
        </button>
      </div>

      <ListingFilters filters={filters} onChange={setFilters} />

      {isLoading ? (
        <div className="py-12 text-center text-gray-400">Loading listings...</div>
      ) : (
        <ListingGrid
          listings={data?.listings ?? []}
          total={data?.total ?? 0}
          page={filters.page}
          onPageChange={(page) => setFilters((f) => ({ ...f, page }))}
        />
      )}
    </div>
  );
}
