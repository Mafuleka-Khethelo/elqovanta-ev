import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Session } from "../../lib/types";
import { formatDuration, formatWhen } from "../../lib/format";
import { Card, EmptyState, PageHeader, Pagination, Skeleton } from "../../components/ui";

export function HistoryPage() {
  const [offset, setOffset] = useState(0);
  const limit = 10;
  const history = useQuery({
    queryKey: ["history", offset],
    queryFn: () => api<{ items: Session[]; total: number; limit: number; offset: number }>(`/sessions/history?limit=${limit}&offset=${offset}`),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="My history" lede="Your finished charging sessions." />
      {history.isLoading ? <Skeleton className="h-40" /> : null}
      {history.data && history.data.total === 0 ? <EmptyState title="No completed sessions" message="Sessions appear here after you report unplugging." /> : null}
      <div className="space-y-3">
        {history.data?.items.map((item) => (
          <Card key={item.id}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h2 className="font-semibold">{item.charger_name}</h2>
                <p className="text-sm text-slate-500">Unplugged {formatWhen(item.unplugged_at)}</p>
              </div>
              {item.is_demonstration ? <p className="text-xs font-semibold text-amber-800">Demonstration activity</p> : null}
            </div>
            <p className="mt-2 text-sm text-slate-600">
              Connected {formatDuration(item.connected_seconds)} · Charging {formatDuration(item.charging_seconds)} · Not charging {formatDuration(item.noncharging_seconds)}
            </p>
          </Card>
        ))}
      </div>
      {history.data && history.data.total > 0 ? <Pagination offset={offset} limit={limit} total={history.data.total} onPage={setOffset} /> : null}
    </div>
  );
}
