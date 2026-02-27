"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useToastStore } from "@/hooks/useToast";

interface BrandProfile {
  id: string;
  name: string;
  is_default: boolean;
  voice_description: string | null;
  vocabulary: string[];
  avoid_words: string[];
  sample_content: string | null;
}

interface BrandProfileFormData {
  name: string;
  voice_description: string;
  vocabulary: string;
  avoid_words: string;
  sample_content: string;
  is_default: boolean;
}

const emptyFormData: BrandProfileFormData = {
  name: "",
  voice_description: "",
  vocabulary: "",
  avoid_words: "",
  sample_content: "",
  is_default: false,
};

function formDataFromProfile(profile: BrandProfile): BrandProfileFormData {
  return {
    name: profile.name,
    voice_description: profile.voice_description ?? "",
    vocabulary: profile.vocabulary?.join(", ") ?? "",
    avoid_words: profile.avoid_words?.join(", ") ?? "",
    sample_content: profile.sample_content ?? "",
    is_default: profile.is_default,
  };
}

export default function BrandProfilesPage() {
  const queryClient = useQueryClient();
  const toast = useToastStore((s) => s.toast);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<BrandProfileFormData>({
    ...emptyFormData,
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editFormData, setEditFormData] = useState<BrandProfileFormData>({
    ...emptyFormData,
  });

  const { data: profiles, isLoading } = useQuery<BrandProfile[]>({
    queryKey: ["brand-profiles"],
    queryFn: async () => {
      const res = await api.get("/brand-profiles");
      return res.data;
    },
  });

  const createProfile = useMutation({
    mutationFn: async (data: BrandProfileFormData) => {
      return api.post("/brand-profiles", {
        ...data,
        vocabulary: data.vocabulary
          ? data.vocabulary.split(",").map((s) => s.trim())
          : [],
        avoid_words: data.avoid_words
          ? data.avoid_words.split(",").map((s) => s.trim())
          : [],
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brand-profiles"] });
      setShowForm(false);
      setFormData({ ...emptyFormData });
      toast({ title: "Brand profile created", variant: "success" });
    },
    onError: () => {
      toast({ title: "Failed to create profile", variant: "error" });
    },
  });

  const updateProfile = useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: BrandProfileFormData;
    }) => {
      return api.patch(`/brand-profiles/${id}`, {
        ...data,
        vocabulary: data.vocabulary
          ? data.vocabulary.split(",").map((s) => s.trim())
          : [],
        avoid_words: data.avoid_words
          ? data.avoid_words.split(",").map((s) => s.trim())
          : [],
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brand-profiles"] });
      setEditingId(null);
      setEditFormData({ ...emptyFormData });
      toast({ title: "Brand profile updated", variant: "success" });
    },
    onError: () => {
      toast({ title: "Failed to update profile", variant: "error" });
    },
  });

  const deleteProfile = useMutation({
    mutationFn: async (id: string) => {
      return api.delete(`/brand-profiles/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brand-profiles"] });
      toast({ title: "Brand profile deleted", variant: "success" });
    },
    onError: () => {
      toast({ title: "Failed to delete profile", variant: "error" });
    },
  });

  function handleEdit(profile: BrandProfile) {
    setEditingId(profile.id);
    setEditFormData(formDataFromProfile(profile));
  }

  function handleCancelEdit() {
    setEditingId(null);
    setEditFormData({ ...emptyFormData });
  }

  function handleDelete(profile: BrandProfile) {
    if (!window.confirm("Delete this brand profile?")) return;
    deleteProfile.mutate(profile.id);
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Brand Profiles</h1>
          <p className="text-sm text-gray-500">
            Define your brand voice for AI-generated content
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light"
        >
          {showForm ? "Cancel" : "New Profile"}
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="mb-4 font-semibold text-gray-800">
            Create Brand Profile
          </h3>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Profile Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData((f) => ({ ...f, name: e.target.value }))
                }
                placeholder='e.g. "Galt Ocean Luxury" or "Agent Dennis Casual"'
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Voice Description
              </label>
              <textarea
                value={formData.voice_description}
                onChange={(e) =>
                  setFormData((f) => ({
                    ...f,
                    voice_description: e.target.value,
                  }))
                }
                rows={3}
                placeholder="Professional, warm, emphasizes ocean lifestyle and investment value..."
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Preferred Words (comma-separated)
              </label>
              <input
                type="text"
                value={formData.vocabulary}
                onChange={(e) =>
                  setFormData((f) => ({ ...f, vocabulary: e.target.value }))
                }
                placeholder="coastal, exclusive, premier, sun-drenched"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Words to Avoid (comma-separated)
              </label>
              <input
                type="text"
                value={formData.avoid_words}
                onChange={(e) =>
                  setFormData((f) => ({ ...f, avoid_words: e.target.value }))
                }
                placeholder="cheap, deal, fixer-upper, cozy"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Sample Content
              </label>
              <textarea
                value={formData.sample_content}
                onChange={(e) =>
                  setFormData((f) => ({
                    ...f,
                    sample_content: e.target.value,
                  }))
                }
                rows={3}
                placeholder="Paste an example of your desired writing style..."
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_default"
                checked={formData.is_default}
                onChange={(e) =>
                  setFormData((f) => ({ ...f, is_default: e.target.checked }))
                }
              />
              <label htmlFor="is_default" className="text-sm text-gray-700">
                Set as default profile
              </label>
            </div>
            <button
              onClick={() => createProfile.mutate(formData)}
              disabled={!formData.name || createProfile.isPending}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
            >
              {createProfile.isPending ? "Creating..." : "Create Profile"}
            </button>
          </div>
        </div>
      )}

      {/* Profile List */}
      <div className="space-y-4">
        {isLoading ? (
          <p className="text-center text-gray-400">Loading...</p>
        ) : profiles?.length ? (
          profiles.map((profile: BrandProfile) => (
            <div
              key={profile.id}
              className="rounded-lg border border-gray-200 bg-white p-6"
            >
              {editingId === profile.id ? (
                /* ---- Edit Mode ---- */
                <div className="space-y-4">
                  <h3 className="mb-2 font-semibold text-gray-800">
                    Edit Brand Profile
                  </h3>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Profile Name
                    </label>
                    <input
                      type="text"
                      value={editFormData.name}
                      onChange={(e) =>
                        setEditFormData((f) => ({
                          ...f,
                          name: e.target.value,
                        }))
                      }
                      placeholder='e.g. "Galt Ocean Luxury" or "Agent Dennis Casual"'
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Voice Description
                    </label>
                    <textarea
                      value={editFormData.voice_description}
                      onChange={(e) =>
                        setEditFormData((f) => ({
                          ...f,
                          voice_description: e.target.value,
                        }))
                      }
                      rows={3}
                      placeholder="Professional, warm, emphasizes ocean lifestyle and investment value..."
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Preferred Words (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={editFormData.vocabulary}
                      onChange={(e) =>
                        setEditFormData((f) => ({
                          ...f,
                          vocabulary: e.target.value,
                        }))
                      }
                      placeholder="coastal, exclusive, premier, sun-drenched"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Words to Avoid (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={editFormData.avoid_words}
                      onChange={(e) =>
                        setEditFormData((f) => ({
                          ...f,
                          avoid_words: e.target.value,
                        }))
                      }
                      placeholder="cheap, deal, fixer-upper, cozy"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">
                      Sample Content
                    </label>
                    <textarea
                      value={editFormData.sample_content}
                      onChange={(e) =>
                        setEditFormData((f) => ({
                          ...f,
                          sample_content: e.target.value,
                        }))
                      }
                      rows={3}
                      placeholder="Paste an example of your desired writing style..."
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={`is_default_edit_${profile.id}`}
                      checked={editFormData.is_default}
                      onChange={(e) =>
                        setEditFormData((f) => ({
                          ...f,
                          is_default: e.target.checked,
                        }))
                      }
                    />
                    <label
                      htmlFor={`is_default_edit_${profile.id}`}
                      className="text-sm text-gray-700"
                    >
                      Set as default profile
                    </label>
                  </div>
                  <div className="mt-4 flex gap-3">
                    <button
                      onClick={() =>
                        updateProfile.mutate({
                          id: profile.id,
                          data: editFormData,
                        })
                      }
                      disabled={
                        !editFormData.name || updateProfile.isPending
                      }
                      className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
                    >
                      {updateProfile.isPending ? "Saving..." : "Save"}
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                /* ---- View Mode ---- */
                <>
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {profile.name}
                    </h3>
                    {profile.is_default && (
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                        Default
                      </span>
                    )}
                  </div>
                  {profile.voice_description && (
                    <p className="mt-2 text-sm text-gray-600">
                      {profile.voice_description}
                    </p>
                  )}
                  {profile.vocabulary?.length > 0 && (
                    <div className="mt-3">
                      <span className="text-xs font-medium text-gray-500">
                        Preferred:{" "}
                      </span>
                      <span className="text-xs text-gray-600">
                        {profile.vocabulary.join(", ")}
                      </span>
                    </div>
                  )}
                  {profile.avoid_words?.length > 0 && (
                    <div className="mt-1">
                      <span className="text-xs font-medium text-gray-500">
                        Avoid:{" "}
                      </span>
                      <span className="text-xs text-gray-600">
                        {profile.avoid_words.join(", ")}
                      </span>
                    </div>
                  )}
                  {profile.sample_content && (
                    <div className="mt-1">
                      <span className="text-xs font-medium text-gray-500">
                        Sample:{" "}
                      </span>
                      <span className="text-xs text-gray-600">
                        {profile.sample_content.length > 100
                          ? profile.sample_content.slice(0, 100) + "..."
                          : profile.sample_content}
                      </span>
                    </div>
                  )}
                  <div className="mt-4 flex gap-3">
                    <button
                      onClick={() => handleEdit(profile)}
                      className="text-sm text-primary hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(profile)}
                      className="text-sm text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))
        ) : (
          <p className="py-8 text-center text-sm text-gray-400">
            No brand profiles yet. Create one to customize your AI-generated
            content.
          </p>
        )}
      </div>
    </div>
  );
}
