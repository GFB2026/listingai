"use client";

import { useState } from "react";
import api from "@/lib/api";

interface Props {
  contentId: string;
}

const FORMATS = [
  { value: "txt", label: "Plain Text (.txt)" },
  { value: "html", label: "HTML (.html)" },
  { value: "docx", label: "Word (.docx)" },
  { value: "pdf", label: "PDF (.pdf)" },
];

export function ExportMenu({ contentId }: Props) {
  const [open, setOpen] = useState(false);

  const handleExport = async (format: string) => {
    const response = await api.get(`/content/${contentId}/export/${format}`, {
      responseType: "blob",
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = `content-${contentId}.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        Export
      </button>

      {open && (
        <>
          <div className="fixed inset-0" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full z-10 mt-1 w-48 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
            {FORMATS.map((fmt) => (
              <button
                key={fmt.value}
                onClick={() => handleExport(fmt.value)}
                className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
              >
                {fmt.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
