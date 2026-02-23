"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useListings } from "@/hooks/useListings";
import { ListingGrid } from "@/components/listings/ListingGrid";
import { ListingFilters } from "@/components/listings/ListingFilters";
import { useMlsConnections } from "@/hooks/useMlsConnections";
import api from "@/lib/api";

export default function ListingsPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    status: "",
    property_type: "",
    city: "",
    min_price: "",
    max_price: "",
    bedrooms: "",
    bathrooms: "",
    page: 1,
  });

  const { data, isLoading } = useListings(filters);
  const { data: connectionsData } = useMlsConnections();
  const [syncing, setSyncing] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);

  const firstConnection = connectionsData?.connections?.[0];

  const triggerSync = async () => {
    setSyncing(true);
    setSyncFeedback(null);
    try {
      await api.post("/listings/sync");
      setSyncFeedback("MLS sync triggered. Listings will update shortly.");
      // Refresh listings after a delay to pick up new data
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["listings"] });
        queryClient.invalidateQueries({ queryKey: ["mls-connections"] });
      }, 3000);
    } catch {
      setSyncFeedback("Failed to trigger sync.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Listings</h1>
          <p className="text-sm text-gray-500">
            {data?.total ?? 0} listings synced from MLS
            {firstConnection?.last_sync_at &&
              ` · Last sync: ${new Date(firstConnection.last_sync_at).toLocaleString()}`}
          </p>
        </div>
        <button
          onClick={triggerSync}
          disabled={syncing}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
        >
          {syncing ? "Syncing..." : "Sync MLS"}
        </button>
      </div>

      {syncFeedback && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          {syncFeedback}
        </div>
      )}

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
