"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import api from "@/lib/api";
import { useToastStore } from "@/hooks/useToast";

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message;
  }
  return error instanceof Error ? error.message : "An unexpected error occurred";
}

export default function BillingPage() {
  const queryClient = useQueryClient();

  const { data: usage, isLoading } = useQuery({
    queryKey: ["billing", "usage"],
    queryFn: async () => {
      const res = await api.get("/billing/usage");
      return res.data;
    },
  });

  const subscribe = useMutation({
    mutationFn: async (priceId: string) => {
      const res = await api.post("/billing/subscribe", null, { params: { price_id: priceId } });
      return res.data;
    },
    onSuccess: (data) => {
      // If the response has a URL (Stripe checkout), redirect to it
      if (data.url) {
        window.location.href = data.url;
      } else {
        // Otherwise refresh usage data
        queryClient.invalidateQueries({ queryKey: ["billing", "usage"] });
        useToastStore.getState().toast({
          title: "Subscription updated",
          description: `Your plan has been updated to ${data.status}.`,
          variant: "success",
        });
      }
    },
    onError: (error) => {
      useToastStore.getState().toast({
        title: "Subscription failed",
        description: getErrorMessage(error),
        variant: "error",
      });
    },
  });

  const isPaidPlan = usage?.plan && usage.plan !== "free";

  const plans = [
    {
      name: "Free",
      price: "$0",
      limit: "50 generations/mo",
      priceId: null as string | null,
      current: usage?.plan === "free",
    },
    {
      name: "Starter",
      price: "$49/mo",
      limit: "200 generations/mo",
      priceId: "price_starter",
      current: usage?.plan === "starter",
    },
    {
      name: "Professional",
      price: "$149/mo",
      limit: "1,000 generations/mo",
      priceId: "price_professional",
      current: usage?.plan === "professional",
    },
    {
      name: "Enterprise",
      price: "Custom",
      limit: "10,000+ generations/mo",
      priceId: "price_enterprise",
      current: usage?.plan === "enterprise",
    },
  ];

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        Usage & Billing
      </h1>

      {/* Current Usage */}
      <div className="mb-8 rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">
          Current Period Usage
        </h2>
        {isLoading ? (
          <p className="text-gray-400">Loading...</p>
        ) : (
          <div className="space-y-4">
            <div>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-gray-600">
                  {usage?.credits_used ?? 0} / {usage?.credits_limit ?? 50}{" "}
                  generations used
                </span>
                <span className="text-gray-400">
                  {usage?.credits_remaining ?? 0} remaining
                </span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{
                    width: `${Math.min(100, ((usage?.credits_used ?? 0) / (usage?.credits_limit ?? 50)) * 100)}%`,
                  }}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Tokens Used</p>
                <p className="text-lg font-semibold text-gray-900">
                  {(usage?.tokens_used ?? 0).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-gray-500">Total Events</p>
                <p className="text-lg font-semibold text-gray-900">
                  {usage?.total_events ?? 0}
                </p>
              </div>
              <div>
                <p className="text-gray-500">Current Plan</p>
                <p className="text-lg font-semibold text-gray-900 capitalize">
                  {usage?.plan ?? "free"}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Plans */}
      <h2 className="mb-4 text-lg font-semibold text-gray-800">Plans</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`rounded-lg border p-6 ${
              plan.current
                ? "border-primary bg-primary/5"
                : "border-gray-200 bg-white"
            }`}
          >
            <h3 className="text-lg font-semibold text-gray-900">
              {plan.name}
            </h3>
            <p className="mt-1 text-2xl font-bold text-primary">
              {plan.price}
            </p>
            <p className="mt-2 text-sm text-gray-600">{plan.limit}</p>
            {plan.current ? (
              <>
                <p className="mt-4 text-sm font-medium text-primary">
                  Current Plan
                </p>
                {isPaidPlan && (
                  <p className="mt-2 text-xs text-gray-500">
                    Contact support to change or cancel your plan.
                  </p>
                )}
              </>
            ) : plan.priceId ? (
              <button
                onClick={() => subscribe.mutate(plan.priceId!)}
                disabled={subscribe.isPending}
                className="mt-4 w-full rounded-lg border border-primary px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary hover:text-white disabled:opacity-50"
              >
                {subscribe.isPending ? "Processing..." : "Upgrade"}
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
