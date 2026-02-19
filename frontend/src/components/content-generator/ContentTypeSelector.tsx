"use client";

import { CONTENT_TYPES } from "@/lib/utils";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

export function ContentTypeSelector({ value, onChange }: Props) {
  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-gray-700">
        Content Type
      </label>
      <div className="grid grid-cols-2 gap-2">
        {CONTENT_TYPES.map((ct) => (
          <button
            key={ct.value}
            onClick={() => onChange(ct.value)}
            className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
              value === ct.value
                ? "border-primary bg-primary/5 font-medium text-primary"
                : "border-gray-200 text-gray-600 hover:border-gray-300"
            }`}
          >
            {ct.label}
          </button>
        ))}
      </div>
    </div>
  );
}
