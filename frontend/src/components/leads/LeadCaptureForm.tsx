"use client";

import { useState, type FormEvent } from "react";
import publicApi from "@/lib/public-api";
import { getStoredUtm, getOrCreateSessionId } from "@/lib/utm";
import { cn } from "@/lib/utils";
import { ThankYouMessage } from "./ThankYouMessage";

interface LeadCaptureFormProps {
  tenantSlug: string;
  agentSlug: string;
  listingId?: string;
  propertyInterest?: string;
  agentName?: string;
  onSuccess?: () => void;
}

interface FormData {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  message: string;
  property_interest: string;
}

interface FormErrors {
  first_name?: string;
  email?: string;
}

export function LeadCaptureForm({
  tenantSlug,
  agentSlug,
  listingId,
  propertyInterest,
  agentName,
  onSuccess,
}: LeadCaptureFormProps) {
  const [formData, setFormData] = useState<FormData>({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    message: "",
    property_interest: propertyInterest ?? "",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  function validate(): boolean {
    const newErrors: FormErrors = {};

    if (!formData.first_name.trim()) {
      newErrors.first_name = "First name is required";
    }

    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Please enter a valid email address";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear field error on change
    if (name in errors) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    if (!validate()) return;

    setIsSubmitting(true);

    try {
      const utm = getStoredUtm();
      const sessionId = getOrCreateSessionId();

      await publicApi.post("/leads", {
        tenant_slug: tenantSlug,
        agent_slug: agentSlug,
        listing_id: listingId ?? null,
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim() || null,
        email: formData.email.trim() || null,
        phone: formData.phone.trim() || null,
        message: formData.message.trim() || null,
        property_interest: formData.property_interest.trim() || null,
        utm_source: utm.utm_source ?? null,
        utm_medium: utm.utm_medium ?? null,
        utm_campaign: utm.utm_campaign ?? null,
        utm_content: utm.utm_content ?? null,
        utm_term: utm.utm_term ?? null,
        session_id: sessionId || null,
        referrer_url: typeof document !== "undefined" ? document.referrer || null : null,
        landing_url: typeof window !== "undefined" ? window.location.href : null,
      });

      setIsSuccess(true);
      onSuccess?.();
    } catch {
      setSubmitError("Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isSuccess) {
    return <ThankYouMessage agentName={agentName} />;
  }

  return (
    <section className="bg-white px-4 py-8 md:py-12" id="contact">
      <div className="mx-auto max-w-lg">
        <h2 className="mb-1 text-center text-xl font-bold text-primary md:text-2xl">
          Get in Touch
        </h2>
        <p className="mb-6 text-center text-sm text-gray-400">
          Interested in this property? Send a message and we will respond promptly.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {/* First & Last name */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="first_name"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                First Name <span className="text-red-500">*</span>
              </label>
              <input
                id="first_name"
                name="first_name"
                type="text"
                required
                value={formData.first_name}
                onChange={handleChange}
                className={cn(
                  "w-full rounded-lg border px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-300 focus:border-primary focus:ring-1 focus:ring-primary",
                  errors.first_name ? "border-red-400" : "border-gray-300"
                )}
                placeholder="John"
              />
              {errors.first_name && (
                <p className="mt-1 text-xs text-red-500">{errors.first_name}</p>
              )}
            </div>
            <div>
              <label
                htmlFor="last_name"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Last Name
              </label>
              <input
                id="last_name"
                name="last_name"
                type="text"
                value={formData.last_name}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-300 focus:border-primary focus:ring-1 focus:ring-primary"
                placeholder="Doe"
              />
            </div>
          </div>

          {/* Email & Phone */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="email"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                className={cn(
                  "w-full rounded-lg border px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-300 focus:border-primary focus:ring-1 focus:ring-primary",
                  errors.email ? "border-red-400" : "border-gray-300"
                )}
                placeholder="john@example.com"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-500">{errors.email}</p>
              )}
            </div>
            <div>
              <label
                htmlFor="phone"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Phone
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-300 focus:border-primary focus:ring-1 focus:ring-primary"
                placeholder="(555) 123-4567"
              />
            </div>
          </div>

          {/* Property interest */}
          <div>
            <label
              htmlFor="property_interest"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Property of Interest
            </label>
            <input
              id="property_interest"
              name="property_interest"
              type="text"
              value={formData.property_interest}
              onChange={handleChange}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-300 focus:border-primary focus:ring-1 focus:ring-primary"
              placeholder="e.g. 3000 N Ocean Blvd #1234"
            />
          </div>

          {/* Message */}
          <div>
            <label
              htmlFor="message"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Message
            </label>
            <textarea
              id="message"
              name="message"
              rows={3}
              value={formData.message}
              onChange={handleChange}
              className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-300 focus:border-primary focus:ring-1 focus:ring-primary"
              placeholder="I'd like to schedule a showing..."
            />
          </div>

          {/* Submit error */}
          {submitError && (
            <p className="text-center text-sm text-red-500">{submitError}</p>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-accent py-3 text-sm font-semibold text-primary transition-colors hover:bg-accent-light disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Sending..." : "Send Message"}
          </button>
        </form>
      </div>
    </section>
  );
}
