import { FormEvent, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api, newRequestKey } from "../../lib/api";
import { formatDuration, formatWhen, stateLabel, statusLabel } from "../../lib/format";
import { Badge, Button, Card, Dialog, EmptyState, ErrorPanel, Field, PageHeader, SelectInput, Skeleton, SourceNote, TextInput } from "../../components/ui";
import { HelpReports } from "../coordination/HelpReports";
import { RefreshNotice, useOffline } from "../coordination/Updates";


type ManagerCharger = {
  id: string;
  station_key: string;
  timezone: string;
  display_name: string;
  is_historical: boolean;
  app_status: string;
  status_updated_at: string | null;
  status_source: string | null;
  service_capacity: number | null;
  coordination_enabled: boolean;
  port_types: { name: string; origin: string }[];
  sessions: { id: string; driver_name: string; state: string; is_demonstration: boolean; plugged_in_at: string; connected_seconds: number; charging_seconds: number; noncharging_seconds: number }[];
  queue: { user_id: string; driver_name: string; state: string; joined_at: string; offer_expires_at: string | null; is_demonstration: boolean }[];
};

export { ManagerHomePage } from "./ManagerDashboard";

export function ManagerChargerPage() {
  const { chargerId = "" } = useParams();
  const queryClient = useQueryClient();
  const offline = useOffline();
  const charger = useQuery({
    queryKey: ["manager-charger", chargerId],
    queryFn: () => api<ManagerCharger>(`/manager/chargers/${chargerId}`),
    refetchInterval: () => (document.visibilityState === "visible" ? 8000 : false),
    refetchIntervalInBackground: false,
  });
  const [status, setStatus] = useState("");
  const [capacity, setCapacity] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [port, setPort] = useState("");
  const [timezone, setTimezone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [closing, setClosing] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [pending, setPending] = useState(false);
  const closeKey = useRef(newRequestKey());

  async function save(event: FormEvent) {
    event.preventDefault();
    if (pending || (charger.isError || charger.isPaused || offline)) return;
    setPending(true);
    setError(null);
    const body: Record<string, unknown> = {};
    if (displayName.trim()) body.display_name = displayName.trim();
    if (status) body.app_status = status;
    if (capacity) body.service_capacity = Number(capacity);
    if (port.trim()) body.port_types_to_add = [port.trim()];
    if (timezone) body.timezone = timezone;
    try {
      await api(`/manager/chargers/${chargerId}`, { method: "PATCH", body });
      setPort("");
      await queryClient.invalidateQueries({ queryKey: ["manager-charger", chargerId] });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not update the charger.");
    } finally { setPending(false); }
  }

  async function closeSession() {
    if (!closing || pending || (charger.isError || charger.isPaused || offline)) return;
    setPending(true);
    setError(null);
    try {
      await api(`/manager/chargers/${chargerId}/sessions/${closing}/close`, {
        method: "POST",
        body: { reason, idempotency_key: closeKey.current },
      });
      setClosing(null);
      setReason("");
      await queryClient.invalidateQueries({ queryKey: ["manager-charger", chargerId] });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not close the session.");
    } finally { setPending(false); }
  }

  async function remind(userId: string) {
    if (pending || (charger.isError || charger.isPaused || offline)) return;
    setPending(true);
    setError(null);
    try {
      await api(`/manager/chargers/${chargerId}/remind`, { method: "POST", body: { user_id: userId } });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not send the reminder.");
    } finally { setPending(false); }
  }

  if (charger.isLoading) return <Skeleton className="h-48" />;
  if (!charger.data) return <ErrorPanel message="This charger is not assigned to you, or it could not be loaded." />;
  const item = charger.data;

  return (
    <div className="space-y-4">
      <PageHeader title={item.display_name} lede="Update the status drivers see, and review who is charging or waiting." />
      {error ? <ErrorPanel message={error} /> : null}
      <RefreshNotice failed={(charger.isError || charger.isPaused || offline)} updatedAt={charger.dataUpdatedAt} />
      <SourceNote>Last update {formatWhen(item.status_updated_at)}{item.status_source ? ` by ${item.status_source}` : ""}. Current label: {statusLabel(item.app_status)}.</SourceNote>
      <form className="grid gap-3 md:grid-cols-2" onSubmit={(event) => void save(event)}>
        <Field label="Display name">
          <TextInput value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder={item.display_name} />
        </Field>
        <Field label="App-reported status">
          <SelectInput value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Keep current</option>
            <option value="available">Reported available</option>
            <option value="occupied">Reported occupied</option>
            <option value="paused">Coordination closed</option>
            <option value="offline">Offline</option>
            <option value="unknown">Not reported</option>
          </SelectInput>
        </Field>
        <Field label="Service capacity" hint="Cannot be set below slots already taken by sessions or open offers.">
          <TextInput type="number" min={1} max={20} value={capacity} placeholder={item.service_capacity ? String(item.service_capacity) : "Not set"} onChange={(event) => setCapacity(event.target.value)} />
        </Field>
        <Field label="Add an observed port label"><TextInput value={port} onChange={(event) => setPort(event.target.value)} /></Field>
        <Field label="Charger timezone" hint={`Current timezone: ${item.timezone}. This controls current station report times.`}><SelectInput value={timezone} onChange={event=>setTimezone(event.target.value)}><option value="">Keep current</option><option value="America/Los_Angeles">Palo Alto / Los Angeles</option><option value="Africa/Johannesburg">Johannesburg</option><option value="Europe/London">London</option><option value="UTC">UTC</option></SelectInput></Field>
        <Button type="submit" disabled={pending || (charger.isError || charger.isPaused || offline)}>{pending ? "Updating…" : "Save charger settings"}</Button>
      </form>
      <section>
        <h2 className="mb-2 font-semibold">Open app sessions</h2>
        {item.sessions.length === 0 ? <EmptyState title="No open sessions" message="Drivers have not reported an active session at this charger." /> : null}
        <div className="space-y-3">
          {item.sessions.map((session) => (
            <Card key={session.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold">{session.driver_name}</p>
                <Badge tone="blue">{stateLabel(session.state)}</Badge>
              </div>
              <p className="mt-1 text-sm text-slate-600">Since {formatWhen(session.plugged_in_at)} · connected {formatDuration(session.connected_seconds)} · charging {formatDuration(session.charging_seconds)} · not charging {formatDuration(session.noncharging_seconds)}</p>
              {session.is_demonstration ? <p className="text-xs text-amber-800">Demonstration activity</p> : null}
              <Button className="mt-3" variant="danger" disabled={pending || (charger.isError || charger.isPaused || offline)} onClick={() => {closeKey.current=newRequestKey();setClosing(session.id);}}>Close abandoned session</Button>
            </Card>
          ))}
        </div>
      </section>
      <section>
        <h2 className="mb-2 font-semibold">Waiting list</h2>
        {item.queue.length === 0 ? <p className="text-sm text-slate-600">Nobody is waiting or holding an offer.</p> : null}
        {item.queue.map((entry) => (
          <Card key={entry.user_id} className="mb-2">
            <p className="font-semibold">{entry.driver_name} · {entry.state}</p>
            <p className="text-sm text-slate-500">Joined {formatWhen(entry.joined_at)}{entry.offer_expires_at ? ` · offer until ${formatWhen(entry.offer_expires_at)}` : ""}</p>
            {entry.is_demonstration ? <p className="text-xs text-amber-800">Demonstration activity</p> : null}
            <Button className="mt-2" variant="secondary" disabled={pending || (charger.isError || charger.isPaused || offline)} onClick={() => void remind(entry.user_id)}>Send a polite reminder</Button>
          </Card>
        ))}
      </section>
      <HelpReports chargerId={chargerId} manager />
      <Link className="text-sm font-semibold text-primary" to="/app/messages">Open related messages</Link>
      <Dialog title="Close this session" open={closing !== null} onClose={() => {if(!pending)setClosing(null);}}>
        <p className="text-sm text-slate-600">Record why you are closing it. This does not charge a fee.</p>
        <Field label="Reason">
          <TextInput value={reason} onChange={(event) => setReason(event.target.value)} minLength={5} />
        </Field>
        <div className="mt-3 flex gap-2">
          <Button variant="danger" disabled={pending || (charger.isError || charger.isPaused || offline)} onClick={() => void closeSession()}>Close session</Button>
          <Button variant="secondary" disabled={pending} onClick={() => setClosing(null)}>Cancel</Button>
        </div>
      </Dialog>
    </div>
  );
}
