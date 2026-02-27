"use client";

import { useState } from "react";
import Link from "next/link";
import { useSocialStatus, usePublishSocial } from "@/hooks/useSocial";
import type { SocialPostResult } from "@/hooks/useSocial";

export default function SocialMediaPage() {
  const { data: status, isLoading: statusLoading } = useSocialStatus();
  const publishMutation = usePublishSocial();

  const [fbText, setFbText] = useState("");
  const [igText, setIgText] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");
  const [listingLink, setListingLink] = useState("");
  const [results, setResults] = useState<SocialPostResult[] | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setResults(null);
    publishMutation.mutate(
      {
        fb_text: fbText || undefined,
        ig_text: igText || undefined,
        photo_url: photoUrl || undefined,
        listing_link: listingLink || undefined,
      },
      {
        onSuccess: (data) => {
          setResults(data.results);
        },
      }
    );
  };

  const bothEmpty = !fbText.trim() && !igText.trim();

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Social Media</h1>

      <div className="max-w-2xl space-y-6">
        {/* Status Card */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            Connection Status
          </h2>
          {statusLoading ? (
            <p className="text-sm text-gray-400">Loading...</p>
          ) : (
            <div className="flex items-center gap-4">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                  status?.facebook
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-500"
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    status?.facebook ? "bg-green-500" : "bg-gray-400"
                  }`}
                />
                Facebook
              </span>
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                  status?.instagram
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-500"
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    status?.instagram ? "bg-green-500" : "bg-gray-400"
                  }`}
                />
                Instagram
              </span>
            </div>
          )}
        </div>

        {/* Not configured message */}
        {!statusLoading && !status?.configured && (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <p className="text-sm text-gray-600">
              Configure social credentials in tenant settings.{" "}
              <Link
                href="/settings"
                className="font-medium text-primary hover:underline"
              >
                Go to Settings
              </Link>
            </p>
          </div>
        )}

        {/* Publish Form */}
        {!statusLoading && status?.configured && (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-800">
              Publish Post
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Facebook Text
                </label>
                <textarea
                  value={fbText}
                  onChange={(e) => setFbText(e.target.value)}
                  maxLength={5000}
                  rows={4}
                  placeholder="Write your Facebook post..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <p className="mt-1 text-xs text-gray-400">
                  {fbText.length}/5000
                </p>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Instagram Text
                </label>
                <textarea
                  value={igText}
                  onChange={(e) => setIgText(e.target.value)}
                  maxLength={2200}
                  rows={4}
                  placeholder="Write your Instagram caption..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <p className="mt-1 text-xs text-gray-400">
                  {igText.length}/2200
                </p>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Photo URL
                </label>
                <input
                  type="text"
                  value={photoUrl}
                  onChange={(e) => setPhotoUrl(e.target.value)}
                  placeholder="https://example.com/photo.jpg"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Listing Link
                </label>
                <input
                  type="text"
                  value={listingLink}
                  onChange={(e) => setListingLink(e.target.value)}
                  placeholder="https://example.com/listing/123"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              <button
                type="submit"
                disabled={bothEmpty || publishMutation.isPending}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
              >
                {publishMutation.isPending ? "Publishing..." : "Publish"}
              </button>
            </form>
          </div>
        )}

        {/* Results */}
        {results && results.length > 0 && (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-800">
              Results
            </h2>
            <div className="space-y-3">
              {results.map((r, i) => (
                <div
                  key={i}
                  className={`rounded-lg border p-3 text-sm ${
                    r.success
                      ? "border-green-200 bg-green-50 text-green-800"
                      : "border-red-200 bg-red-50 text-red-800"
                  }`}
                >
                  <span className="font-medium capitalize">{r.platform}</span>
                  {" — "}
                  {r.success ? "Published" : "Failed"}
                  {r.post_id && (
                    <span className="ml-2 text-xs text-gray-500">
                      (ID: {r.post_id})
                    </span>
                  )}
                  {r.error && (
                    <p className="mt-1 text-xs">{r.error}</p>
                  )}
                  {r.warning && (
                    <p className="mt-1 text-xs text-yellow-700">{r.warning}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
