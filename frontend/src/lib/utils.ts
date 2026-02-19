import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(price);
}

export function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + "...";
}

export const CONTENT_TYPES = [
  { value: "listing_description", label: "Listing Description" },
  { value: "social_instagram", label: "Instagram Post" },
  { value: "social_facebook", label: "Facebook Post" },
  { value: "social_linkedin", label: "LinkedIn Post" },
  { value: "social_x", label: "X (Twitter) Post" },
  { value: "email_just_listed", label: "Just Listed Email" },
  { value: "email_open_house", label: "Open House Email" },
  { value: "email_drip", label: "Drip Campaign Email" },
  { value: "flyer", label: "Flyer Copy" },
  { value: "video_script", label: "Video Script" },
] as const;

export const TONES = [
  { value: "luxury", label: "Luxury" },
  { value: "professional", label: "Professional" },
  { value: "casual", label: "Casual" },
  { value: "friendly", label: "Friendly" },
  { value: "urgent", label: "Urgent" },
] as const;
