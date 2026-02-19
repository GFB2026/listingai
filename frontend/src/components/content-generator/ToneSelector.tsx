"use client";

import { TONES } from "@/lib/utils";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

export function ToneSelector({ value, onChange }: Props) {
  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-gray-700">
        Tone
      </label>
      <div className="flex flex-wrap gap-2">
        {TONES.map((tone) => (
          <button
            key={tone.value}
            onClick={() => onChange(tone.value)}
            className={`rounded-full border px-4 py-1.5 text-sm transition-colors ${
              value === tone.value
                ? "border-primary bg-primary text-white"
                : "border-gray-200 text-gray-600 hover:border-gray-300"
            }`}
          >
            {tone.label}
          </button>
        ))}
      </div>
    </div>
  );
}
