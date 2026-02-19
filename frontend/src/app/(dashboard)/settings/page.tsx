"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function SettingsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { data: tenant } = useQuery({
    queryKey: ["tenant"],
    queryFn: async () => {
      const res = await api.get("/tenants/current");
      return res.data;
    },
  });

  const [name, setName] = useState("");

  const updateTenant = useMutation({
    mutationFn: (data: { name: string }) => api.patch("/tenants/current", data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tenant"] }),
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Settings</h1>

      <div className="max-w-2xl space-y-6">
        {/* Brokerage Info */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            Brokerage Information
          </h2>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Brokerage Name
              </label>
              <input
                type="text"
                defaultValue={tenant?.name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Slug
              </label>
              <input
                type="text"
                value={tenant?.slug || ""}
                disabled
                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Plan
              </label>
              <input
                type="text"
                value={tenant?.plan || "free"}
                disabled
                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500"
              />
            </div>
            <button
              onClick={() => updateTenant.mutate({ name: name || tenant?.name })}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light"
            >
              Save Changes
            </button>
          </div>
        </div>

        {/* User Info */}
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            Your Account
          </h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Email</dt>
              <dd className="text-gray-900">{user?.email}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Name</dt>
              <dd className="text-gray-900">{user?.full_name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Role</dt>
              <dd className="text-gray-900">{user?.role}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
