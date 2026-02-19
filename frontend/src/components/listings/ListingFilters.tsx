"use client";

interface Filters {
  status: string;
  property_type: string;
  city: string;
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

      {(filters.status || filters.property_type || filters.city) && (
        <button
          onClick={() =>
            onChange({ status: "", property_type: "", city: "", page: 1 })
          }
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
