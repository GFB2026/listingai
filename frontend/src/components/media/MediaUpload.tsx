"use client";

import { useCallback, useRef, useState } from "react";
import { useUploadMedia, type MediaUploadResponse } from "@/hooks/useMedia";

interface MediaUploadProps {
  onUploaded: (response: MediaUploadResponse) => void;
  accept?: string;
  label?: string;
}

const DEFAULT_ACCEPT = "image/jpeg,image/png,image/webp,application/pdf";
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

type UploadState = "idle" | "uploading" | "success" | "error";

export default function MediaUpload({
  onUploaded,
  accept = DEFAULT_ACCEPT,
  label = "Upload File",
}: MediaUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const uploadMutation = useUploadMedia();

  const isImage = (file: File) => file.type.startsWith("image/");

  const clearPreview = useCallback(() => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
  }, [previewUrl]);

  const processFile = useCallback(
    (file: File) => {
      setErrorMessage(null);
      clearPreview();

      if (file.size > MAX_FILE_SIZE) {
        setErrorMessage(
          `File size (${(file.size / 1024 / 1024).toFixed(1)}MB) exceeds the 10MB limit.`
        );
        setUploadState("error");
        return;
      }

      const acceptedTypes = accept.split(",").map((t) => t.trim());
      if (!acceptedTypes.includes(file.type)) {
        setErrorMessage(
          `File type "${file.type}" is not accepted. Accepted types: ${accept}`
        );
        setUploadState("error");
        return;
      }

      setSelectedFile(file);
      setUploadState("uploading");

      uploadMutation.mutate(file, {
        onSuccess: (response) => {
          setUploadState("success");
          if (isImage(file)) {
            setPreviewUrl(URL.createObjectURL(file));
          }
          onUploaded(response);
        },
        onError: () => {
          setUploadState("error");
          setErrorMessage("Upload failed. Please try again.");
        },
      });
    },
    [accept, clearPreview, onUploaded, uploadMutation]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      const file = e.dataTransfer.files?.[0];
      if (file) {
        processFile(file);
      }
    },
    [processFile]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        processFile(file);
      }
    },
    [processFile]
  );

  const handleClick = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const dropZoneClass = dragActive
    ? "rounded-lg border-2 border-dashed border-primary bg-primary/5 p-8 text-center cursor-pointer"
    : "rounded-lg border-2 border-dashed border-gray-300 p-8 text-center hover:border-primary cursor-pointer";

  return (
    <div className="space-y-3">
      <div
        className={dropZoneClass}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleClick();
          }
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleFileChange}
          className="hidden"
          aria-label={label}
        />

        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">{label}</p>
          <p className="text-xs text-gray-500">
            Drag and drop or click to browse. Max 10MB.
          </p>
        </div>
      </div>

      {selectedFile && (
        <div className="text-sm text-gray-600">
          <span className="font-medium">Selected:</span> {selectedFile.name} (
          {(selectedFile.size / 1024).toFixed(1)}KB)
        </div>
      )}

      {uploadState === "uploading" && (
        <div className="text-sm text-blue-600">Uploading...</div>
      )}

      {uploadState === "success" && (
        <div className="text-sm text-green-600">Upload complete.</div>
      )}

      {uploadState === "error" && errorMessage && (
        <div className="text-sm text-red-600">{errorMessage}</div>
      )}

      {previewUrl && (
        <div className="mt-2">
          <img
            src={previewUrl}
            alt={`Preview of ${selectedFile?.name ?? "uploaded file"}`}
            className="h-32 w-32 rounded-lg object-cover"
          />
        </div>
      )}
    </div>
  );
}
