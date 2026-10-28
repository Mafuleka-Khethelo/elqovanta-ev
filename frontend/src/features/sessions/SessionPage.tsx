import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, newRequestKey } from "../../lib/api";
import type { Session } from "../../lib/types";
import { eventLabel, formatDuration, formatWhen, stateLabel } from "../../lib/format";
import { Badge, Button, Card, EmptyState, ErrorPanel, PageHeader, Skeleton, SourceNote } from "../../components/ui";
import { ChargerGuidance } from "../chargers/ChargerGuidance";
import { SessionCoordination } from "../coordination/SessionCoordination";
import { RefreshNotice, useOffline } from "../coordination/Updates";

export function SessionPage() {
  const queryClient = useQueryClient();
  const offline = useOffline();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [keys] = useState<Record<string, string>>({});
  const [tick, setTick] = useState(Date.now());
  const session = useQuery({
    queryKey: ["session"],
    queryFn: () => api<{ session: Session | null; server_time: string }>("/sessions/current"),
    refetchInterval: () => (document.visibilityState === "visible" ? 5000 : false),
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    const id = window.setInterval(() => setTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  async function act(name: string, path: string) {
    const key = keys[name] ?? newRequestKey();
    keys[name] = key;
    setPending(true);
    setError(null);
    try {
      await api(path, { method: "POST", body: { idempotency_key: key } });
      delete keys[name];
      await queryClient.invalidateQueries({ queryKey: ["session"] });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The request failed.");
    } finally {
      setPending(false);
    }
  }

  if (session.isLoading) return <Skeleton className="h-48" />;
  const current = session.data?.session;
  if (!current) {
    if ((session.isError || session.isPaused || offline)) return <ErrorPanel message="Your session could not be loaded. Refresh to try again." />;
    return (
      <div>
        <PageHeader title="My charging session" />
        <EmptyState title="No open session" message="Start from a charger only when an app slot is free and nobody is already waiting." action={<Link className="font-semibold text-primary" to="/app/chargers">Find chargers</Link>} />
      </div>
    );
  }

  const durations = liveDurations(current, session.dataUpdatedAt, (session.isError || session.isPaused || offline) ? session.errorUpdatedAt : tick);

  return (
    <div className="space-y-4">
      <PageHeader title={current.charger_name} />
      {current.is_demonstration ? <SourceNote>This is demonstration activity.</SourceNote> : null}
      {error ? <ErrorPanel message={error} /> : null}
      <RefreshNotice failed={(session.isError || session.isPaused || offline)} updatedAt={session.dataUpdatedAt} />
      <div className="grid gap-3 md:grid-cols-3">
        <Card><p className="text-sm text-slate-500">Connected</p><p className="text-2xl font-semibold">{formatDuration(durations.connected)}</p></Card>
        <Card><p className="text-sm text-slate-500">Charging</p><p className="text-2xl font-semibold">{formatDuration(durations.charging)}</p></Card>
        <Card><p className="text-sm text-slate-500">Not charging</p><p className="text-2xl font-semibold">{formatDuration(durations.noncharging)}</p></Card>
      </div>
      <Card>
        <Badge tone="blue">{stateLabel(current.state)}</Badge>
        <p className="mt-2 text-sm text-slate-600">Plugged in {formatWhen(current.plugged_in_at)}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {current.state === "charging" ? <Button disabled={pending || (session.isError || session.isPaused || offline)} onClick={() => void act("pause", `/sessions/${current.id}/pause`)}>Pause charging</Button> : null}
          {(current.state === "paused" || current.state === "finished_plugged") ? <Button disabled={pending || (session.isError || session.isPaused || offline)} onClick={() => void act("resume", `/sessions/${current.id}/resume`)}>Resume charging</Button> : null}
          {current.state === "charging" || current.state === "paused" ? <Button variant="secondary" disabled={pending || (session.isError || session.isPaused || offline)} onClick={() => void act("finish", `/sessions/${current.id}/finish`)}>Charging finished, still plugged in</Button> : null}
          <Button variant="danger" disabled={pending || (session.isError || session.isPaused || offline)} onClick={() => void act("unplug", `/sessions/${current.id}/unplug`)}>Report unplugged</Button>
          {current.state === "charging" ? <Button variant="ghost" disabled={pending || (session.isError || session.isPaused || offline)} onClick={() => void act("still", `/sessions/${current.id}/still-charging`)}>I am still charging</Button> : null}
        </div>
      </Card>
      <ChargerGuidance key={`advisory-${current.id}`} chargerId={current.charger_id} sessionId={current.id} />
      <SessionCoordination key={`coordination-${current.id}`} sessionId={current.id} state={current.state} stale={(session.isError || session.isPaused || offline)} />
      <Link className="inline-block text-sm font-semibold underline underline-offset-4" to={`/app/chargers/${current.charger_id}`}>Open charger details, contact manager and quick help</Link>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Timeline</h2>
        <ol className="space-y-2">
          {current.events.map((event) => (
            <li key={event.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
              <p className="font-medium">{eventLabel(event.event_type)}</p>
              <p className="text-slate-500">{formatWhen(event.created_at)}{event.actor_name ? ` · ${event.actor_name}` : ""}</p>
              {event.reason ? <p className="mt-1 whitespace-pre-wrap">{event.reason}</p> : null}
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function liveDurations(session: Session, receivedAt: number, now: number) {
  if (session.unplugged_at || !receivedAt) {
    return { connected: session.connected_seconds, charging: session.charging_seconds, noncharging: session.noncharging_seconds };
  }
  const extra = Math.max(0, Math.floor((now - receivedAt) / 1000));
  const connected = session.connected_seconds + extra;
  const charging = session.state === "charging" ? session.charging_seconds + extra : session.charging_seconds;
  return { connected, charging, noncharging: Math.max(0, connected - charging) };
}
