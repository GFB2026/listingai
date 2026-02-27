"use client";

import { useState } from "react";
import {
  useEmailStatus,
  useEmailCampaigns,
  useSendEmail,
  type EmailSendResponse,
} from "@/hooks/useEmailCampaigns";

const CAMPAIGN_TYPES = [
  { value: "manual", label: "Manual" },
  { value: "just_listed", label: "Just Listed" },
  { value: "open_house", label: "Open House" },
  { value: "price_reduction", label: "Price Reduction" },
  { value: "just_sold", label: "Just Sold" },
  { value: "agent_notify", label: "Agent Notify" },
  { value: "custom", label: "Custom" },
];

export default function EmailPage() {
  const [page, setPage] = useState(1);
  const [recipients, setRecipients] = useState("");
  const [subject, setSubject] = useState("");
  const [htmlContent, setHtmlContent] = useState("");
  const [campaignType, setCampaignType] = useState("manual");
  const [sendResult, setSendResult] = useState<EmailSendResponse | null>(null);

  const { data: status, isLoading: statusLoading } = useEmailStatus();
  const { data: campaigns, isLoading: campaignsLoading } = useEmailCampaigns({ page });
  const sendEmail = useSendEmail();

  const handleSend = () => {
    const toEmails = recipients
      .split(",")
      .map((e) => e.trim())
      .filter(Boolean);

    if (toEmails.length === 0 || !subject || !htmlContent) return;

    setSendResult(null);
    sendEmail.mutate(
      {
        to_emails: toEmails,
        subject,
        html_content: htmlContent,
        campaign_type: campaignType,
      },
      {
        onSuccess: (data) => {
          setSendResult(data);
          setRecipients("");
          setSubject("");
          setHtmlContent("");
          setCampaignType("manual");
        },
      }
    );
  };

  const pageSize = 20;
  const totalPages = campaigns ? Math.ceil(campaigns.total / pageSize) : 0;

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Email Campaigns</h1>

      {/* Campaign History */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">
          Campaign History
        </h2>

        {campaignsLoading ? (
          <p className="py-8 text-center text-sm text-gray-400">Loading...</p>
        ) : campaigns?.campaigns?.length ? (
          <>
            <div className="overflow-hidden rounded-lg border border-gray-200">
              <table className="w-full text-sm">
                <thead className="border-b bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">
                      Subject
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">
                      Type
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">
                      Sent
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">
                      Failed
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {campaigns.campaigns.map((c) => (
                    <tr key={c.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {c.subject}
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {c.campaign_type.replace(/_/g, " ")}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{c.sent}</td>
                      <td className="px-4 py-3 text-gray-600">{c.failed}</td>
                      <td className="px-4 py-3 text-gray-400">
                        {new Date(c.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {campaigns.total > pageSize && (
              <div className="mt-4 flex justify-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded border px-3 py-1 text-sm disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-3 py-1 text-sm text-gray-600">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= totalPages}
                  className="rounded border px-3 py-1 text-sm disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </>
        ) : (
          <p className="py-8 text-center text-sm text-gray-400">
            No campaigns sent yet.
          </p>
        )}
      </div>

      {/* Send Email */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">
          Send Email
        </h2>

        {statusLoading ? (
          <p className="py-4 text-center text-sm text-gray-400">
            Checking email configuration...
          </p>
        ) : !status?.configured ? (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
            SendGrid is not configured. Please add your SendGrid API key in
            Settings to enable email campaigns.
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Recipients (comma-separated emails)
              </label>
              <input
                type="text"
                value={recipients}
                onChange={(e) => setRecipients(e.target.value)}
                placeholder="alice@example.com, bob@example.com"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Subject
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Your email subject line"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                HTML Content
              </label>
              <textarea
                value={htmlContent}
                onChange={(e) => setHtmlContent(e.target.value)}
                placeholder="<p>Your email body here...</p>"
                rows={6}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Campaign Type
              </label>
              <select
                value={campaignType}
                onChange={(e) => setCampaignType(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                {CAMPAIGN_TYPES.map((ct) => (
                  <option key={ct.value} value={ct.value}>
                    {ct.label}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleSend}
              disabled={
                sendEmail.isPending ||
                !recipients.trim() ||
                !subject.trim() ||
                !htmlContent.trim()
              }
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
            >
              {sendEmail.isPending ? "Sending..." : "Send Campaign"}
            </button>

            {sendResult && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
                <p className="font-medium text-gray-800">Send Results</p>
                <p className="mt-1 text-gray-600">
                  Sent: {sendResult.sent} | Failed: {sendResult.failed}
                </p>
                {sendResult.errors.length > 0 && (
                  <ul className="mt-2 list-disc pl-5 text-red-600">
                    {sendResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
