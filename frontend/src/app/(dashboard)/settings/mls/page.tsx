"use client";

import { useState } from "react";
import axios from "axios";
import {
  useMlsConnections,
  useCreateMlsConnection,
  useTestMlsConnection,
  useDeleteMlsConnection,
  useMlsConnectionStatus,
} from "@/hooks/useMlsConnections";

export default function MLSSettingsPage() {
  const { data, isLoading } = useMlsConnections();
  const createMutation = useCreateMlsConnection();
  const testMutation = useTestMlsConnection();
  const deleteMutation = useDeleteMlsConnection();

  const [form, setForm] = useState({
    provider: "trestle",
    name: "",
    base_url: "",
    client_id: "",
    client_secret: "",
  });
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [selectedStatusId, setSelectedStatusId] = useState<string | null>(null);

  const { data: statusData } = useMlsConnectionStatus(selectedStatusId);

  const resetForm = () => {
    setForm({
      provider: "trestle",
      name: "",
      base_url: "",
      client_id: "",
      client_secret: "",
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);

    if (!form.name || !form.base_url || !form.client_id || !form.client_secret) {
      setFeedback({ type: "error", message: "All fields are required." });
      return;
    }

    try {
      await createMutation.mutateAsync(form);
      setFeedback({
        type: "success",
        message: "MLS connection created successfully.",
      });
      resetForm();
    } catch (err: unknown) {
      setFeedback({
        type: "error",
        message: axios.isAxiosError(err)
          ? err.response?.data?.detail || "Failed to create MLS connection."
          : "Failed to create MLS connection.",
      });
    }
  };

  const handleTest = async (connectionId: string) => {
    setFeedback(null);
    try {
      const result = await testMutation.mutateAsync(connectionId);
      setFeedback({
        type: result.success ? "success" : "error",
        message: result.message,
      });
    } catch {
      setFeedback({ type: "error", message: "Failed to test connection." });
    }
  };

  const handleDelete = async (connectionId: string) => {
    if (!confirm("Are you sure you want to delete this MLS connection?")) return;
    setFeedback(null);
    try {
      await deleteMutation.mutateAsync(connectionId);
      setFeedback({ type: "success", message: "Connection deleted." });
      if (selectedStatusId === connectionId) setSelectedStatusId(null);
    } catch {
      setFeedback({ type: "error", message: "Failed to delete connection." });
    }
  };

  const connections = data?.connections ?? [];

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        MLS Connection Settings
      </h1>

      {feedback && (
        <div
          className={`mb-4 rounded-lg px-4 py-3 text-sm ${
            feedback.type === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {feedback.message}
        </div>
      )}

      <div className="max-w-2xl space-y-6">
        {/* Create Connection Form */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            Connect Your MLS
          </h2>
          <p className="mb-4 text-sm text-gray-600">
            Connect your RESO Web API (Trestle) credentials to automatically
            sync listings from your MLS.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                MLS Provider
              </label>
              <select
                value={form.provider}
                onChange={(e) =>
                  setForm((f) => ({ ...f, provider: e.target.value }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="trestle">Trestle (CoreLogic)</option>
                <option value="bridge">Bridge Interactive</option>
                <option value="spark">Spark API</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Connection Name
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value }))
                }
                placeholder="e.g. Beaches MLS"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                API Base URL
              </label>
              <input
                type="url"
                value={form.base_url}
                onChange={(e) =>
                  setForm((f) => ({ ...f, base_url: e.target.value }))
                }
                placeholder="https://api-trestle.corelogic.com"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Client ID
              </label>
              <input
                type="text"
                value={form.client_id}
                onChange={(e) =>
                  setForm((f) => ({ ...f, client_id: e.target.value }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Client Secret
              </label>
              <input
                type="password"
                value={form.client_secret}
                onChange={(e) =>
                  setForm((f) => ({ ...f, client_secret: e.target.value }))
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
            >
              {createMutation.isPending ? "Saving..." : "Save Connection"}
            </button>
          </form>
        </div>

        {/* Existing Connections */}
        {isLoading ? (
          <div className="py-8 text-center text-gray-400">
            Loading connections...
          </div>
        ) : connections.length > 0 ? (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-800">
              Your MLS Connections
            </h2>
            <div className="space-y-4">
              {connections.map((conn) => (
                <div
                  key={conn.id}
                  className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-4"
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      {conn.name || conn.provider}
                    </p>
                    <p className="text-xs text-gray-500">
                      {conn.provider} &middot; {conn.base_url}
                    </p>
                    <p className="text-xs text-gray-400">
                      {conn.sync_enabled ? "Sync enabled" : "Sync disabled"}
                      {conn.last_sync_at &&
                        ` · Last sync: ${new Date(conn.last_sync_at).toLocaleString()}`}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() =>
                        setSelectedStatusId(
                          selectedStatusId === conn.id ? null : conn.id
                        )
                      }
                      className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100"
                    >
                      Status
                    </button>
                    <button
                      onClick={() => handleTest(conn.id)}
                      disabled={testMutation.isPending}
                      className="rounded border border-blue-300 px-3 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50 disabled:opacity-50"
                    >
                      {testMutation.isPending ? "Testing..." : "Test"}
                    </button>
                    <button
                      onClick={() => handleDelete(conn.id)}
                      disabled={deleteMutation.isPending}
                      className="rounded border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Sync Status Panel */}
            {selectedStatusId && statusData && (
              <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-4">
                <h3 className="mb-2 text-sm font-semibold text-blue-900">
                  Sync Status: {statusData.name || "Connection"}
                </h3>
                <dl className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <dt className="text-blue-600">Listings Synced</dt>
                    <dd className="font-medium text-blue-900">
                      {statusData.listing_count}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-blue-600">Sync Enabled</dt>
                    <dd className="font-medium text-blue-900">
                      {statusData.sync_enabled ? "Yes" : "No"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-blue-600">Last Sync</dt>
                    <dd className="font-medium text-blue-900">
                      {statusData.last_sync_at
                        ? new Date(statusData.last_sync_at).toLocaleString()
                        : "Never"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-blue-600">Watermark</dt>
                    <dd className="font-medium text-blue-900">
                      {statusData.sync_watermark || "—"}
                    </dd>
                  </div>
                </dl>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
