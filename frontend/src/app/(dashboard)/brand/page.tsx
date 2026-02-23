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

export default function BrandProfilesPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    voice_description: "",
    vocabulary: "",
    avoid_words: "",
    sample_content: "",
    is_default: false,
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
      setFormData({
        name: "",
        voice_description: "",
        vocabulary: "",
        avoid_words: "",
        sample_content: "",
        is_default: false,
      });
    },
  });

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
