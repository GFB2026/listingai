"use client";

export default function MLSSettingsPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        MLS Connection Settings
      </h1>

      <div className="max-w-2xl">
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-800">
            Connect Your MLS
          </h2>
          <p className="mb-4 text-sm text-gray-600">
            Connect your RESO Web API (Trestle) credentials to automatically
            sync listings from your MLS.
          </p>

          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                MLS Provider
              </label>
              <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="trestle">Trestle (CoreLogic)</option>
                <option value="bridge">Bridge Interactive</option>
                <option value="spark">Spark API</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Connection Name
              </label>
              <input
                type="text"
                placeholder="e.g. Beaches MLS"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                API Base URL
              </label>
              <input
                type="url"
                placeholder="https://api-trestle.corelogic.com"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Client ID
              </label>
              <input
                type="text"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Client Secret
              </label>
              <input
                type="password"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <button className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light">
              Save & Test Connection
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
