"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface Props {
  value: string | null;
  onChange: (value: string | null) => void;
}

export function BrandVoiceSelector({ value, onChange }: Props) {
  const { data: profiles } = useQuery({
    queryKey: ["brand-profiles"],
    queryFn: async () => {
      const res = await api.get("/brand-profiles");
      return res.data;
    },
  });

  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">
        Brand Voice
      </label>
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value || null)}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
        <option value="">Use default (or none)</option>
        {profiles?.map((profile: any) => (
          <option key={profile.id} value={profile.id}>
            {profile.name}
            {profile.is_default ? " (Default)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
