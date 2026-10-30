import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Session } from "../../lib/types";
import { formatDuration, formatWhen } from "../../lib/format";
import { Card, EmptyState, ErrorPanel, PageHeader, Pagination, Skeleton } from "../../components/ui";

export function HistoryPage() {
  const [offset, setOffset] = useState(0);
  const limit = 10;
  const history = useQuery({
    queryKey: ["history", offset],
    queryFn: () => api<{ items: Session[]; total: number; limit: number; offset: number }>(`/sessions/history?limit=${limit}&offset=${offset}`),
  });

  return (
    <div className="space-y-4">
      <PageHeader title="My session summaries" lede="Your completed visits, based on your charging and unplug reports." />
      {history.isError ? <ErrorPanel message="Your session summaries could not be refreshed. Last loaded records are shown." /> : null}
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
            <dl className="mt-4 grid gap-3 sm:grid-cols-3">{[["Connected", item.connected_seconds],["Reported charging", item.charging_seconds],["Connected without charging", item.noncharging_seconds]].map(([label,seconds]) => <div key={label}><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 text-lg font-semibold">{formatDuration(Number(seconds))}</dd></div>)}</dl>
            {item.charge_summary ? <p className="mt-3 text-sm text-slate-600">{item.charge_summary.vehicle_label} · Planned target: {item.charge_summary.target_percent}% · Last entered reading: {item.charge_summary.last_entered_percent}%. Battery completion and energy delivered were not measured.</p> : null}
            {item.return_reminder_sent_at ? <p className="mt-2 text-xs text-primary">Optional return reminder sent {formatWhen(item.return_reminder_sent_at)}</p> : null}
          </Card>
        ))}
      </div>
      {history.data && history.data.total > 0 ? <Pagination offset={offset} limit={limit} total={history.data.total} onPage={setOffset} /> : null}
    </div>
  );
}
