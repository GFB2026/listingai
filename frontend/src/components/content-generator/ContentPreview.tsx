"use client";

import { useState } from "react";

interface ContentItem {
  id: string;
  content_type: string;
  tone: string;
  body: string;
  metadata: Record<string, any>;
  ai_model: string;
  version: number;
}

interface Props {
  content?: ContentItem[];
  usage?: { credits_consumed: number; credits_remaining: number };
  isLoading: boolean;
}

export function ContentPreview({ content, usage, isLoading }: Props) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!content?.[activeIndex]) return;
    await navigator.clipboard.writeText(content[activeIndex].body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-gray-200 bg-white">
        <div className="text-center">
          <div className="mb-2 text-gray-400">Generating with Claude AI...</div>
          <div className="text-xs text-gray-300">This may take a few seconds</div>
        </div>
      </div>
    );
  }

  if (!content?.length) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50">
        <p className="text-sm text-gray-400">
          Select options and click Generate to create content
        </p>
      </div>
    );
  }

  const active = content[activeIndex];

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Variant tabs */}
      {content.length > 1 && (
        <div className="flex border-b border-gray-200">
          {content.map((_, i) => (
            <button
              key={i}
              onClick={() => setActiveIndex(i)}
              className={`px-4 py-2 text-sm font-medium ${
                i === activeIndex
                  ? "border-b-2 border-primary text-primary"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Variant {i + 1}
            </button>
          ))}
        </div>
      )}

      {/* Content body */}
      <div className="p-6">
        <div className="mb-4 whitespace-pre-wrap text-sm leading-relaxed text-gray-800">
          {active.body}
        </div>

        {/* Metadata */}
        {active.metadata && (
          <div className="mb-4 flex flex-wrap gap-2 text-xs text-gray-400">
            {active.metadata.word_count && (
              <span>{active.metadata.word_count} words</span>
            )}
            {active.metadata.character_count && (
              <span>{active.metadata.character_count} chars</span>
            )}
            <span>Model: {active.ai_model}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
          <button className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
            Export
          </button>
        </div>
      </div>

      {/* Usage footer */}
      {usage && (
        <div className="border-t border-gray-100 px-6 py-3 text-xs text-gray-400">
          {usage.credits_consumed} credit{usage.credits_consumed !== 1 ? "s" : ""}{" "}
          used | {usage.credits_remaining} remaining
        </div>
      )}
    </div>
  );
}
