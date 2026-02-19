"use client";

import { useState } from "react";
import { useContent } from "@/hooks/useContent";
import { CONTENT_TYPES } from "@/lib/utils";
import Link from "next/link";

export default function ContentLibraryPage() {
  const [contentType, setContentType] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useContent({ content_type: contentType, page });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Content Library</h1>

      {/* Filters */}
      <div className="mb-6 flex gap-3">
        <select
          value={contentType}
          onChange={(e) => {
            setContentType(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All Types</option>
          {CONTENT_TYPES.map((ct) => (
            <option key={ct.value} value={ct.value}>
              {ct.label}
            </option>
          ))}
        </select>
      </div>

      {/* Content List */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        {isLoading ? (
          <p className="px-4 py-8 text-center text-sm text-gray-400">
            Loading...
          </p>
        ) : data?.content?.length ? (
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Type
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Tone
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Preview
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Status
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Created
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.content.map((item: any) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {item.content_type.replace(/_/g, " ")}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{item.tone}</td>
                  <td className="max-w-xs truncate px-4 py-3 text-gray-600">
                    {item.body.slice(0, 80)}...
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        item.status === "approved"
                          ? "bg-green-100 text-green-700"
                          : item.status === "published"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(item.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/content`}
                      className="text-primary hover:underline"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="px-4 py-8 text-center text-sm text-gray-400">
            No content found. Generate content from a listing.
          </p>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > 20 && (
        <div className="mt-4 flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded border px-3 py-1 text-sm disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-sm text-gray-600">
            Page {page} of {Math.ceil(data.total / 20)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * 20 >= data.total}
            className="rounded border px-3 py-1 text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
