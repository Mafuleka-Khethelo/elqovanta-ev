import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Notice } from "../../lib/types";
import { formatWhen } from "../../lib/format";
import { Button, Card, EmptyState, PageHeader, Pagination, Skeleton } from "../../components/ui";

export function NotificationsPage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);
  const limit = 15;
  const notes = useQuery({
    queryKey: ["notifications", offset],
    queryFn: () => api<{ items: Notice[]; total: number }>(`/notifications?limit=${limit}&offset=${offset}`),
    refetchInterval: () => (document.visibilityState === "visible" ? 15000 : false),
    refetchIntervalInBackground: false,
  });

  async function mark(id: string) {
    await api(`/notifications/${id}/read`, { method: "POST" });
    await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    await queryClient.invalidateQueries({ queryKey: ["unread"] });
  }

  async function markAll() {
    await api("/notifications/read-all", { method: "POST" });
    await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    await queryClient.invalidateQueries({ queryKey: ["unread"] });
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Notifications" />
      <Button variant="secondary" onClick={() => void markAll()}>Mark all as read</Button>
      {notes.isLoading ? <Skeleton /> : null}
      {notes.data && notes.data.total === 0 ? <EmptyState title="No notifications" message="Offers, messages and manager changes that affect you will appear here." /> : null}
      <div className="space-y-3">
        {notes.data?.items.map((item) => (
          <Card key={item.id} className={item.read_at ? "" : "border-teal"}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold">{item.title}</h2>
                <p className="mt-1 text-sm whitespace-pre-wrap text-slate-700">{item.body}</p>
                <p className="mt-2 text-xs text-slate-500">{formatWhen(item.created_at)}{item.read_at ? " · Read" : " · Unread"}</p>
              </div>
              <div className="flex gap-2">
                {item.destination.startsWith("/") ? <Link className="text-sm font-semibold text-primary" to={item.destination}>Open</Link> : null}
                {!item.read_at ? <Button variant="secondary" onClick={() => void mark(item.id)}>Mark read</Button> : null}
              </div>
            </div>
          </Card>
        ))}
      </div>
      {notes.data && notes.data.total > limit ? <Pagination offset={offset} limit={limit} total={notes.data.total} onPage={setOffset} /> : null}
    </div>
  );
}
