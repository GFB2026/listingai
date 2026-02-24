"use client";

import { useState } from "react";
import {
  useAgentPages,
  useCreateAgentPage,
  useUpdateAgentPage,
  useDeleteAgentPage,
} from "@/hooks/useAgentPages";
import { cn } from "@/lib/utils";

interface AgentPageFormData {
  user_id: string;
  slug: string;
  headline: string;
  bio: string;
  phone: string;
  email_display: string;
  theme: string;
}

const EMPTY_FORM: AgentPageFormData = {
  user_id: "",
  slug: "",
  headline: "",
  bio: "",
  phone: "",
  email_display: "",
  theme: "default",
};

export default function AgentPagesSettingsPage() {
  const { data, isLoading } = useAgentPages();
  const createMutation = useCreateAgentPage();
  const updateMutation = useUpdateAgentPage();
  const deleteMutation = useDeleteAgentPage();

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<AgentPageFormData>(EMPTY_FORM);

  const agentPages = data?.agent_pages ?? [];

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setShowForm(false);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.user_id || !form.slug) return;

    const payload: Record<string, string> = {
      user_id: form.user_id,
      slug: form.slug,
    };
    if (form.headline) payload.headline = form.headline;
    if (form.bio) payload.bio = form.bio;
    if (form.phone) payload.phone = form.phone;
    if (form.email_display) payload.email_display = form.email_display;
    if (form.theme && form.theme !== "default") payload.theme = form.theme;

    try {
      await createMutation.mutateAsync(payload as {
        user_id: string;
        slug: string;
        headline?: string;
        bio?: string;
        phone?: string;
        email_display?: string;
        theme?: string;
      });
      resetForm();
    } catch {
      // Error handled by mutation onError
    }
  };

  const handleEdit = (page: {
    id: string;
    user_id: string;
    slug: string;
    headline: string | null;
    bio: string | null;
    phone: string | null;
    email_display: string | null;
    theme: string | null;
  }) => {
    setEditingId(page.id);
    setForm({
      user_id: page.user_id,
      slug: page.slug,
      headline: page.headline || "",
      bio: page.bio || "",
      phone: page.phone || "",
      email_display: page.email_display || "",
      theme: page.theme || "default",
    });
    setShowForm(true);
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingId) return;

    try {
      await updateMutation.mutateAsync({
        id: editingId,
        slug: form.slug || undefined,
        headline: form.headline || undefined,
        bio: form.bio || undefined,
        phone: form.phone || undefined,
        email_display: form.email_display || undefined,
        theme: form.theme || undefined,
      });
      resetForm();
    } catch {
      // Error handled by mutation onError
    }
  };

  const handleDeactivate = async (id: string) => {
    if (!confirm("Are you sure you want to deactivate this agent page?")) return;
    try {
      await deleteMutation.mutateAsync(id);
    } catch {
      // Error handled by mutation onError
    }
  };

  const handleToggleActive = async (id: string, currentActive: boolean) => {
    try {
      await updateMutation.mutateAsync({
        id,
        is_active: !currentActive,
      });
    } catch {
      // Error handled by mutation onError
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agent Landing Pages</h1>
          <p className="text-sm text-gray-500">
            Manage agent-specific lead capture pages
          </p>
        </div>
        <button
          onClick={() => {
            resetForm();
            setShowForm(true);
          }}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light"
        >
          Create Page
        </button>
      </div>

      {/* Create / Edit Form */}
      {showForm && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            {editingId ? "Edit Agent Page" : "Create Agent Page"}
          </h2>
          <form
            onSubmit={editingId ? handleUpdate : handleCreate}
            className="grid gap-4 sm:grid-cols-2"
          >
            {!editingId && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  User ID *
                </label>
                <input
                  type="text"
                  value={form.user_id}
                  onChange={(e) => setForm((f) => ({ ...f, user_id: e.target.value }))}
                  placeholder="User UUID"
                  required
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
                />
              </div>
            )}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Slug *
              </label>
              <input
                type="text"
                value={form.slug}
                onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))}
                placeholder="john-doe"
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Headline
              </label>
              <input
                type="text"
                value={form.headline}
                onChange={(e) => setForm((f) => ({ ...f, headline: e.target.value }))}
                placeholder="Your Fort Lauderdale Specialist"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Phone
              </label>
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                placeholder="(954) 555-0123"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Display Email
              </label>
              <input
                type="email"
                value={form.email_display}
                onChange={(e) => setForm((f) => ({ ...f, email_display: e.target.value }))}
                placeholder="agent@brokerage.com"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Theme
              </label>
              <select
                value={form.theme}
                onChange={(e) => setForm((f) => ({ ...f, theme: e.target.value }))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
              >
                <option value="default">Default</option>
                <option value="ocean">Ocean</option>
                <option value="luxury">Luxury</option>
                <option value="modern">Modern</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Bio
              </label>
              <textarea
                value={form.bio}
                onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
                placeholder="Brief agent bio for the landing page..."
                rows={3}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
            </div>
            <div className="flex gap-3 sm:col-span-2">
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? "Saving..."
                  : editingId
                    ? "Update Page"
                    : "Create Page"}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Agent Pages Table */}
      {isLoading ? (
        <div className="py-12 text-center text-gray-400">Loading agent pages...</div>
      ) : agentPages.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white px-6 py-12 text-center">
          <p className="text-sm text-gray-400">
            No agent landing pages yet. Create one to start capturing leads.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Slug
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Agent
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Headline
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {agentPages.map((page) => (
                  <tr key={page.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 text-sm">
                      <span className="font-mono text-primary">/{page.slug}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-900">
                      {page.user_name || page.user_id.slice(0, 8)}
                    </td>
                    <td className="max-w-[200px] truncate px-4 py-3 text-sm text-gray-600">
                      {page.headline || "---"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm">
                      <button
                        onClick={() => handleToggleActive(page.id, page.is_active)}
                        className={cn(
                          "rounded-full px-2.5 py-0.5 text-xs font-medium",
                          page.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        )}
                      >
                        {page.is_active ? "Active" : "Inactive"}
                      </button>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleEdit(page)}
                          className="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeactivate(page.id)}
                          disabled={deleteMutation.isPending}
                          className="rounded border border-red-300 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                        >
                          Deactivate
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
