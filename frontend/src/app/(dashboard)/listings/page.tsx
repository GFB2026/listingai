"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useListings, useCreateListing } from "@/hooks/useListings";
import type { ListingCreateData } from "@/hooks/useListings";
import { ListingGrid } from "@/components/listings/ListingGrid";
import { ListingFilters } from "@/components/listings/ListingFilters";
import { useMlsConnections } from "@/hooks/useMlsConnections";
import api from "@/lib/api";

const INITIAL_FORM: ListingCreateData = {
  address_full: "",
  address_street: "",
  address_city: "",
  address_state: "",
  address_zip: "",
  price: undefined,
  bedrooms: undefined,
  bathrooms: undefined,
  sqft: undefined,
  lot_sqft: undefined,
  year_built: undefined,
  property_type: "",
  status: "active",
  description_original: "",
  features: [],
};

const PROPERTY_TYPES = [
  { value: "", label: "Select type..." },
  { value: "single_family", label: "Single Family" },
  { value: "condo", label: "Condo" },
  { value: "townhouse", label: "Townhouse" },
  { value: "multi_family", label: "Multi Family" },
  { value: "land", label: "Land" },
  { value: "commercial", label: "Commercial" },
  { value: "other", label: "Other" },
];

const STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "pending", label: "Pending" },
  { value: "sold", label: "Sold" },
  { value: "withdrawn", label: "Withdrawn" },
];

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

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showMoreDetails, setShowMoreDetails] = useState(false);
  const [form, setForm] = useState<ListingCreateData>({ ...INITIAL_FORM });
  const [featuresInput, setFeaturesInput] = useState("");

  const createListing = useCreateListing();

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

  const handleSubmit = () => {
    const payload: ListingCreateData = {
      address_full: form.address_full,
    };

    if (form.address_street) payload.address_street = form.address_street;
    if (form.address_city) payload.address_city = form.address_city;
    if (form.address_state) payload.address_state = form.address_state;
    if (form.address_zip) payload.address_zip = form.address_zip;
    if (form.price != null) payload.price = form.price;
    if (form.bedrooms != null) payload.bedrooms = form.bedrooms;
    if (form.bathrooms != null) payload.bathrooms = form.bathrooms;
    if (form.sqft != null) payload.sqft = form.sqft;
    if (form.lot_sqft != null) payload.lot_sqft = form.lot_sqft;
    if (form.year_built != null) payload.year_built = form.year_built;
    if (form.property_type) payload.property_type = form.property_type;
    if (form.status) payload.status = form.status;
    if (form.description_original) payload.description_original = form.description_original;

    const features = featuresInput
      .split(",")
      .map((f) => f.trim())
      .filter(Boolean);
    if (features.length > 0) payload.features = features;

    createListing.mutate(payload, {
      onSuccess: () => {
        setForm({ ...INITIAL_FORM });
        setFeaturesInput("");
        setShowCreateForm(false);
        setShowMoreDetails(false);
      },
    });
  };

  const setField = <K extends keyof ListingCreateData>(key: K, value: ListingCreateData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const parseNumber = (val: string): number | undefined => {
    if (!val) return undefined;
    const n = Number(val);
    return isNaN(n) ? undefined : n;
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Listings</h1>
          <p className="text-sm text-gray-500">
            {data?.total ?? 0} listings synced from MLS
            {firstConnection?.last_sync_at &&
              ` \u00b7 Last sync: ${new Date(firstConnection.last_sync_at).toLocaleString()}`}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCreateForm((v) => !v)}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
          >
            {showCreateForm ? "Cancel" : "Add Listing"}
          </button>
          <button
            onClick={triggerSync}
            disabled={syncing}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
          >
            {syncing ? "Syncing..." : "Sync MLS"}
          </button>
        </div>
      </div>

      {syncFeedback && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          {syncFeedback}
        </div>
      )}

      {showCreateForm && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="mb-4 font-semibold text-gray-800">Add New Listing</h3>

          {/* Required: Full address */}
          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Address (full) <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.address_full}
              onChange={(e) => setField("address_full", e.target.value)}
              placeholder="123 Main St, City, ST 12345"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          {/* Toggle for more details */}
          <button
            type="button"
            onClick={() => setShowMoreDetails((v) => !v)}
            className="mb-4 text-sm text-primary hover:underline"
          >
            {showMoreDetails ? "Hide Details" : "More Details"}
          </button>

          {showMoreDetails && (
            <div className="space-y-4">
              {/* Address parts */}
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Street</label>
                  <input
                    type="text"
                    value={form.address_street ?? ""}
                    onChange={(e) => setField("address_street", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">City</label>
                  <input
                    type="text"
                    value={form.address_city ?? ""}
                    onChange={(e) => setField("address_city", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">State</label>
                  <input
                    type="text"
                    value={form.address_state ?? ""}
                    onChange={(e) => setField("address_state", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Zip</label>
                  <input
                    type="text"
                    value={form.address_zip ?? ""}
                    onChange={(e) => setField("address_zip", e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              {/* Price */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Price</label>
                <input
                  type="number"
                  value={form.price ?? ""}
                  onChange={(e) => setField("price", parseNumber(e.target.value))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              {/* Bed / Bath */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Bedrooms</label>
                  <input
                    type="number"
                    value={form.bedrooms ?? ""}
                    onChange={(e) => setField("bedrooms", parseNumber(e.target.value))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Bathrooms</label>
                  <input
                    type="number"
                    value={form.bathrooms ?? ""}
                    onChange={(e) => setField("bathrooms", parseNumber(e.target.value))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              {/* Sqft / Lot Sqft */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Sqft</label>
                  <input
                    type="number"
                    value={form.sqft ?? ""}
                    onChange={(e) => setField("sqft", parseNumber(e.target.value))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Lot Sqft</label>
                  <input
                    type="number"
                    value={form.lot_sqft ?? ""}
                    onChange={(e) => setField("lot_sqft", parseNumber(e.target.value))}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              {/* Year Built */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Year Built</label>
                <input
                  type="number"
                  value={form.year_built ?? ""}
                  onChange={(e) => setField("year_built", parseNumber(e.target.value))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              {/* Property Type / Status */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Property Type
                  </label>
                  <select
                    value={form.property_type ?? ""}
                    onChange={(e) => setField("property_type", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  >
                    {PROPERTY_TYPES.map((pt) => (
                      <option key={pt.value} value={pt.value}>
                        {pt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Status</label>
                  <select
                    value={form.status ?? "active"}
                    onChange={(e) => setField("status", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
                <textarea
                  value={form.description_original ?? ""}
                  onChange={(e) => setField("description_original", e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              {/* Features */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Features (comma-separated)
                </label>
                <input
                  type="text"
                  value={featuresInput}
                  onChange={(e) => setFeaturesInput(e.target.value)}
                  placeholder="Pool, Ocean View, Garage"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleSubmit}
              disabled={!form.address_full.trim() || createListing.isPending}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
            >
              {createListing.isPending ? "Creating..." : "Create Listing"}
            </button>
            <button
              onClick={() => {
                setShowCreateForm(false);
                setShowMoreDetails(false);
                setForm({ ...INITIAL_FORM });
                setFeaturesInput("");
              }}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
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
