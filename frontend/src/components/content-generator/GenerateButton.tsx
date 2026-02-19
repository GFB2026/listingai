"use client";

interface Props {
  onClick: () => void;
  isLoading: boolean;
}

export function GenerateButton({ onClick, isLoading }: Props) {
  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      className="w-full rounded-lg bg-accent px-6 py-3 text-lg font-semibold text-primary-dark hover:bg-accent-light disabled:opacity-50"
    >
      {isLoading ? (
        <span className="flex items-center justify-center gap-2">
          <svg
            className="h-5 w-5 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Generating...
        </span>
      ) : (
        "Generate Content"
      )}
    </button>
  );
}
