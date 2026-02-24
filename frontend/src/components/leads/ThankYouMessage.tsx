interface ThankYouMessageProps {
  agentName?: string;
}

export function ThankYouMessage({ agentName }: ThankYouMessageProps) {
  return (
    <div className="flex flex-col items-center px-4 py-12 text-center">
      {/* Green checkmark circle */}
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="h-8 w-8 text-green-600"
        >
          <path
            fillRule="evenodd"
            d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
            clipRule="evenodd"
          />
        </svg>
      </div>

      <h2 className="text-xl font-bold text-primary">Thank You!</h2>

      <p className="mt-2 max-w-sm text-sm text-gray-500">
        {agentName
          ? `${agentName} will be in touch with you shortly.`
          : "We'll be in touch with you shortly."}
      </p>
    </div>
  );
}
