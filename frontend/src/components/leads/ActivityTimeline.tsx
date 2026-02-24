"use client";

import { useState } from "react";
import { cn, formatDate } from "@/lib/utils";
import { useAddActivity } from "@/hooks/useLeads";

interface TimelineActivity {
  id: string;
  lead_id: string;
  user_id: string;
  activity_type: string;
  old_value: string | null;
  new_value: string | null;
  note: string | null;
  created_at: string;
  user_name: string | null;
}

interface ActivityTimelineProps {
  activities: TimelineActivity[];
  leadId: string;
}

const ACTIVITY_STYLES: Record<string, { icon: string; color: string; bgColor: string }> = {
  status_change: { icon: "S", color: "text-blue-600", bgColor: "bg-blue-100" },
  note: { icon: "N", color: "text-yellow-600", bgColor: "bg-yellow-100" },
  email_sent: { icon: "E", color: "text-green-600", bgColor: "bg-green-100" },
  call: { icon: "C", color: "text-purple-600", bgColor: "bg-purple-100" },
  meeting: { icon: "M", color: "text-cyan-600", bgColor: "bg-cyan-100" },
  created: { icon: "+", color: "text-gray-600", bgColor: "bg-gray-100" },
};

function getActivityStyle(type: string) {
  return ACTIVITY_STYLES[type] || { icon: "?", color: "text-gray-500", bgColor: "bg-gray-100" };
}

function formatStatusLabel(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function ActivityDescription({ activity }: { activity: TimelineActivity }) {
  const userName = activity.user_name || "System";

  switch (activity.activity_type) {
    case "status_change":
      return (
        <span className="text-sm text-gray-700">
          <span className="font-medium">{userName}</span> changed status from{" "}
          <span className="rounded bg-gray-100 px-1 py-0.5 text-xs font-medium">
            {formatStatusLabel(activity.old_value || "unknown")}
          </span>{" "}
          to{" "}
          <span className="rounded bg-gray-100 px-1 py-0.5 text-xs font-medium">
            {formatStatusLabel(activity.new_value || "unknown")}
          </span>
        </span>
      );
    case "note":
      return (
        <div className="text-sm text-gray-700">
          <span className="font-medium">{userName}</span>
          <span className="ml-1 text-gray-500">added a note</span>
          {activity.note && (
            <p className="mt-1 rounded-lg bg-gray-50 p-2 text-sm text-gray-600 leading-relaxed">
              {activity.note}
            </p>
          )}
        </div>
      );
    default:
      return (
        <span className="text-sm text-gray-700">
          <span className="font-medium">{userName}</span>
          <span className="ml-1 text-gray-500">
            {activity.activity_type.replace(/_/g, " ")}
          </span>
          {activity.note && (
            <p className="mt-1 text-sm text-gray-500">{activity.note}</p>
          )}
        </span>
      );
  }
}

export function ActivityTimeline({ activities, leadId }: ActivityTimelineProps) {
  const [noteText, setNoteText] = useState("");
  const addActivity = useAddActivity();

  const handleSubmitNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteText.trim()) return;

    addActivity.mutate(
      { leadId, activity_type: "note", note: noteText.trim() },
      {
        onSuccess: () => {
          setNoteText("");
        },
      }
    );
  };

  return (
    <div>
      {/* Add note form */}
      <form onSubmit={handleSubmitNote} className="mb-6">
        <label className="mb-1.5 block text-sm font-medium text-gray-700">
          Add a Note
        </label>
        <textarea
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder="Write a note about this lead..."
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
        />
        <button
          type="submit"
          disabled={!noteText.trim() || addActivity.isPending}
          className="mt-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-light disabled:opacity-50"
        >
          {addActivity.isPending ? "Adding..." : "Add Note"}
        </button>
      </form>

      {/* Timeline */}
      <div className="relative">
        {activities.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-400">No activity yet</p>
        ) : (
          <div className="space-y-0">
            {/* Vertical line */}
            <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />

            {activities.map((activity, index) => {
              const style = getActivityStyle(activity.activity_type);

              return (
                <div
                  key={activity.id}
                  className={cn(
                    "relative flex gap-3 pb-6",
                    index === activities.length - 1 && "pb-0"
                  )}
                >
                  {/* Circle icon */}
                  <div
                    className={cn(
                      "relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                      style.bgColor,
                      style.color
                    )}
                  >
                    {style.icon}
                  </div>

                  {/* Content */}
                  <div className="flex-1 pt-0.5">
                    <ActivityDescription activity={activity} />
                    <p className="mt-1 text-[10px] text-gray-400">
                      {formatDate(activity.created_at)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
