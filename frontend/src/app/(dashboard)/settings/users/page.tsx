"use client";

import { useState } from "react";
import {
  useUsers,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  type UserResponse,
} from "@/hooks/useUsers";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface CreateFormData {
  email: string;
  password: string;
  full_name: string;
  role: string;
}

const EMPTY_FORM: CreateFormData = {
  email: "",
  password: "",
  full_name: "",
  role: "agent",
};

export default function UsersSettingsPage() {
  const { user: currentUser } = useAuth();
  const { data, isLoading } = useUsers();
  const createMutation = useCreateUser();
  const updateMutation = useUpdateUser();
  const deleteMutation = useDeleteUser();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateFormData>(EMPTY_FORM);
  const [editingRoleId, setEditingRoleId] = useState<string | null>(null);
  const [editingRoleValue, setEditingRoleValue] = useState<string>("");

  const users = data?.users ?? [];

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setShowForm(false);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.email || !form.password || !form.full_name) return;

    try {
      await createMutation.mutateAsync({
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        role: form.role,
      });
      resetForm();
    } catch {
      // Error handled by mutation onError
    }
  };

  const handleRoleChange = async (user: UserResponse, newRole: string) => {
    try {
      await updateMutation.mutateAsync({ id: user.id, role: newRole });
      setEditingRoleId(null);
    } catch {
      // Error handled by mutation onError
    }
  };

  const handleToggleActive = async (user: UserResponse) => {
    try {
      await updateMutation.mutateAsync({
        id: user.id,
        is_active: !user.is_active,
      });
    } catch {
      // Error handled by mutation onError
    }
  };

  const handleDelete = async (user: UserResponse) => {
    if (currentUser && user.id === currentUser.id) return;
    if (!window.confirm(`Are you sure you want to delete ${user.full_name}?`)) return;

    try {
      await deleteMutation.mutateAsync(user.id);
    } catch {
      // Error handled by mutation onError
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Team Management</h1>
        <button
          onClick={() => {
            resetForm();
            setShowForm(!showForm);
          }}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
        >
          {showForm ? "Cancel" : "Add User"}
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            Add Team Member
          </h2>
          <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Full Name *
              </label>
              <input
                type="text"
                value={form.full_name}
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                placeholder="Jane Agent"
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Email *
              </label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                placeholder="jane@brokerage.com"
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Password *
              </label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                placeholder="Minimum 8 characters"
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Role *
              </label>
              <select
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="admin">Admin</option>
                <option value="broker">Broker</option>
                <option value="agent">Agent</option>
              </select>
            </div>
            <div className="flex gap-3 sm:col-span-2">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
              >
                {createMutation.isPending ? "Creating..." : "Create User"}
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

      {/* User List */}
      {isLoading ? (
        <div className="py-12 text-center text-gray-400">Loading team members...</div>
      ) : users.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white px-6 py-12 text-center">
          <p className="text-sm text-gray-400">
            No team members yet. Add one to get started.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Role
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Status
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map((user) => {
                  const isSelf = currentUser?.id === user.id;

                  return (
                    <tr key={user.id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-4 py-3 font-medium text-gray-900">
                        {user.full_name}
                        {isSelf && (
                          <span className="ml-2 text-xs text-gray-400">(you)</span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-gray-600">
                        {user.email}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        {editingRoleId === user.id ? (
                          <select
                            value={editingRoleValue}
                            onChange={(e) => {
                              setEditingRoleValue(e.target.value);
                              handleRoleChange(user, e.target.value);
                            }}
                            onBlur={() => setEditingRoleId(null)}
                            autoFocus
                            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                          >
                            <option value="admin">Admin</option>
                            <option value="broker">Broker</option>
                            <option value="agent">Agent</option>
                          </select>
                        ) : (
                          <button
                            onClick={() => {
                              setEditingRoleId(user.id);
                              setEditingRoleValue(user.role);
                            }}
                            className="rounded-full px-2.5 py-0.5 text-xs font-medium capitalize bg-blue-100 text-blue-700 hover:bg-blue-200"
                          >
                            {user.role}
                          </button>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <button
                          onClick={() => handleToggleActive(user)}
                          disabled={updateMutation.isPending}
                          className={cn(
                            "rounded-full px-2.5 py-0.5 text-xs font-medium",
                            user.is_active
                              ? "bg-green-100 text-green-700"
                              : "bg-gray-100 text-gray-500"
                          )}
                        >
                          {user.is_active ? "Active" : "Inactive"}
                        </button>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        {!isSelf && (
                          <button
                            onClick={() => handleDelete(user)}
                            disabled={deleteMutation.isPending}
                            className="text-sm text-red-600 hover:text-red-800"
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
