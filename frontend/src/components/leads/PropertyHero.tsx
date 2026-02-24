import { formatPrice } from "@/lib/utils";

interface PropertyListing {
  address_full: string;
  price: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  sqft: number | null;
  year_built: number | null;
  description_original: string | null;
  features: string[] | null;
  photos: Array<{ url: string }> | null;
  property_type: string | null;
}

interface PropertyHeroProps {
  listing: PropertyListing;
}

export function PropertyHero({ listing }: PropertyHeroProps) {
  const heroPhoto = listing.photos?.[0]?.url;

  return (
    <section className="bg-white">
      {/* Hero image */}
      <div className="aspect-[16/9] w-full bg-gray-100 md:aspect-[21/9]">
        {heroPhoto ? (
          <img
            src={heroPhoto}
            alt={listing.address_full}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-lg text-gray-300">
            No Photo Available
          </div>
        )}
      </div>

      <div className="mx-auto max-w-3xl px-4 py-6 md:py-8">
        {/* Price */}
        <p className="text-2xl font-bold text-primary md:text-3xl">
          {listing.price != null ? formatPrice(listing.price) : "Price Upon Request"}
        </p>

        {/* Address */}
        <p className="mt-1 text-base text-gray-600 md:text-lg">
          {listing.address_full}
        </p>

        {/* Property type badge */}
        {listing.property_type && (
          <span className="mt-2 inline-block rounded-full bg-primary/10 px-3 py-0.5 text-xs font-medium text-primary">
            {listing.property_type}
          </span>
        )}

        {/* Key stats */}
        <div className="mt-4 flex flex-wrap gap-4 border-t border-gray-100 pt-4">
          {listing.bedrooms != null && (
            <Stat label="Beds" value={String(listing.bedrooms)} />
          )}
          {listing.bathrooms != null && (
            <Stat label="Baths" value={String(listing.bathrooms)} />
          )}
          {listing.sqft != null && (
            <Stat label="Sq Ft" value={listing.sqft.toLocaleString()} />
          )}
          {listing.year_built != null && (
            <Stat label="Year Built" value={String(listing.year_built)} />
          )}
        </div>

        {/* Description */}
        {listing.description_original && (
          <div className="mt-6">
            <h2 className="mb-2 text-sm font-semibold tracking-wide text-gray-400 uppercase">
              Description
            </h2>
            <p className="text-sm leading-relaxed text-gray-600 whitespace-pre-line">
              {listing.description_original}
            </p>
          </div>
        )}

        {/* Features */}
        {listing.features && listing.features.length > 0 && (
          <div className="mt-6">
            <h2 className="mb-2 text-sm font-semibold tracking-wide text-gray-400 uppercase">
              Features
            </h2>
            <ul className="grid grid-cols-1 gap-x-6 gap-y-1 text-sm text-gray-600 sm:grid-cols-2">
              {listing.features.map((feature) => (
                <li key={feature} className="flex items-center gap-2 py-0.5">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-4 w-4 shrink-0 text-accent"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                      clipRule="evenodd"
                    />
                  </svg>
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center rounded-lg bg-surface px-4 py-2">
      <span className="text-lg font-bold text-primary">{value}</span>
      <span className="text-xs text-gray-400">{label}</span>
    </div>
  );
}
