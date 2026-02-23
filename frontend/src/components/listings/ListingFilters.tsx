"use client";

interface Filters {
  status: string;
  property_type: string;
  city: string;
  min_price: string;
  max_price: string;
  bedrooms: string;
  bathrooms: string;
  page: number;
}

interface Props {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

export function ListingFilters({ filters, onChange }: Props) {
  const update = (key: keyof Filters, value: string) => {
    onChange({ ...filters, [key]: value, page: 1 });
  };

  const hasActiveFilters =
    filters.status ||
    filters.property_type ||
    filters.city ||
    filters.min_price ||
    filters.max_price ||
    filters.bedrooms ||
    filters.bathrooms;

  return (
    <div className="mb-6 flex flex-wrap gap-3">
      <select
        value={filters.status}
        onChange={(e) => update("status", e.target.value)}
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">All Statuses</option>
        <option value="active">Active</option>
        <option value="pending">Pending</option>
        <option value="sold">Sold</option>
        <option value="withdrawn">Withdrawn</option>
      </select>

      <select
        value={filters.property_type}
        onChange={(e) => update("property_type", e.target.value)}
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">All Types</option>
        <option value="residential">Residential</option>
        <option value="condo">Condo</option>
        <option value="townhouse">Townhouse</option>
        <option value="land">Land</option>
        <option value="commercial">Commercial</option>
      </select>

      <input
        type="text"
        value={filters.city}
        onChange={(e) => update("city", e.target.value)}
        placeholder="Filter by city..."
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
      />

      <input
        type="number"
        value={filters.min_price}
        onChange={(e) => update("min_price", e.target.value)}
        placeholder="Min price"
        className="w-28 rounded-lg border border-gray-300 px-3 py-2 text-sm"
      />

      <input
        type="number"
        value={filters.max_price}
        onChange={(e) => update("max_price", e.target.value)}
        placeholder="Max price"
        className="w-28 rounded-lg border border-gray-300 px-3 py-2 text-sm"
      />

      <select
        value={filters.bedrooms}
        onChange={(e) => update("bedrooms", e.target.value)}
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">Beds</option>
        <option value="1">1+</option>
        <option value="2">2+</option>
        <option value="3">3+</option>
        <option value="4">4+</option>
        <option value="5">5+</option>
      </select>

      <select
        value={filters.bathrooms}
        onChange={(e) => update("bathrooms", e.target.value)}
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">Baths</option>
        <option value="1">1+</option>
        <option value="2">2+</option>
        <option value="3">3+</option>
        <option value="4">4+</option>
      </select>

      {hasActiveFilters && (
        <button
          onClick={() =>
            onChange({
              status: "",
              property_type: "",
              city: "",
              min_price: "",
              max_price: "",
              bedrooms: "",
              bathrooms: "",
              page: 1,
            })
          }
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
