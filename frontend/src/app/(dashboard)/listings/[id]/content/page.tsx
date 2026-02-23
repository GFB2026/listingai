"use client";

import { use, useState } from "react";
import { formatPrice, CONTENT_TYPES, TONES } from "@/lib/utils";
import { useListing } from "@/hooks/useListings";
import { useGenerate } from "@/hooks/useGenerate";
import { ContentTypeSelector } from "@/components/content-generator/ContentTypeSelector";
import { ToneSelector } from "@/components/content-generator/ToneSelector";
import { BrandVoiceSelector } from "@/components/content-generator/BrandVoiceSelector";
import { GenerateButton } from "@/components/content-generator/GenerateButton";
import { ContentPreview } from "@/components/content-generator/ContentPreview";

export default function ContentGeneratorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const [contentType, setContentType] = useState("listing_description");
  const [tone, setTone] = useState("professional");
  const [brandProfileId, setBrandProfileId] = useState<string | null>(null);
  const [instructions, setInstructions] = useState("");
  const [variants, setVariants] = useState(1);

  const { data: listing } = useListing(id);

  const { mutate: generate, data: result, isPending } = useGenerate();

  const handleGenerate = () => {
    generate({
      listing_id: id,
      content_type: contentType,
      tone,
      brand_profile_id: brandProfileId,
      instructions: instructions || undefined,
      variants,
    });
  };

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-gray-900">
        Generate Content
      </h1>
      {listing && (
        <p className="mb-6 text-sm text-gray-500">
          {listing.address_full}
          {listing.price ? ` - ${formatPrice(listing.price)}` : ""}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left Panel: Controls */}
        <div className="space-y-6">
          {/* Listing Summary */}
          {listing && (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <h3 className="mb-2 text-sm font-semibold text-gray-700">
                Listing Summary
              </h3>
              <div className="text-sm text-gray-600">
                <p>
                  {listing.bedrooms ?? "?"}BR / {listing.bathrooms ?? "?"}BA
                  {listing.sqft ? ` / ${listing.sqft.toLocaleString()} sqft` : ""}
                </p>
                <p>{listing.property_type} - {listing.status}</p>
                {listing.features?.length > 0 && (
                  <p className="mt-1 text-xs text-gray-400">
                    {listing.features.slice(0, 5).join(", ")}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Content Type */}
          <ContentTypeSelector value={contentType} onChange={setContentType} />

          {/* Tone */}
          <ToneSelector value={tone} onChange={setTone} />

          {/* Brand Voice */}
          <BrandVoiceSelector value={brandProfileId} onChange={setBrandProfileId} />

          {/* Custom Instructions */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Custom Instructions (optional)
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              rows={3}
              placeholder="e.g. Emphasize the ocean view. Include 3 emoji max."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Variants */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Variants
            </label>
            <select
              value={variants}
              onChange={(e) => setVariants(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value={1}>1 variant</option>
              <option value={2}>2 variants</option>
              <option value={3}>3 variants</option>
            </select>
          </div>

          {/* Generate Button */}
          <GenerateButton onClick={handleGenerate} isLoading={isPending} />
        </div>

        {/* Right Panel: Preview */}
        <div>
          <ContentPreview
            content={result?.content}
            usage={result?.usage}
            isLoading={isPending}
          />
        </div>
      </div>
    </div>
  );
}
