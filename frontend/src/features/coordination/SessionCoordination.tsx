import { useEffect, useRef, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, newRequestKey } from "../../lib/api";
import { Button, Card, ErrorPanel, Field, SelectInput, Skeleton, TextInput } from "../../components/ui";
import { RefreshNotice, stationTime } from "./Updates";

type Reminder = { id: string; due_at: string; state: "pending" | "delivered" | "cancelled" };
type Coordination = { server_time: string; timezone: string; departure: { expected_at: string; reported_at: string } | null; reminders: Reminder[]; waiting_count: number };
function deviceInput(value: string) { const date = new Date(value); return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16); }

export function SessionCoordination({ sessionId, state, stale = false }: { sessionId: string; state: string; stale?: boolean }) {
  const client = useQueryClient();
  const detail = useQuery({ queryKey: ["session-coordination", sessionId], queryFn: () => api<Coordination>(`/sessions/${sessionId}/coordination`), refetchInterval: () => document.visibilityState === "visible" ? 5000 : false, refetchIntervalInBackground: false });
  const [expected, setExpected] = useState("");
  const [minutes, setMinutes] = useState("10");
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const requests = useRef<Record<string, { key: string; due: string }>>({});
  useEffect(() => { setExpected(detail.data?.departure ? deviceInput(detail.data.departure.expected_at) : ""); }, [detail.data?.departure?.expected_at]);
  if (detail.isLoading) return <Skeleton className="h-40" />;
  const data = detail.data;
  if (!data) return <Card><ErrorPanel message="Could not load your plans." /><Button className="mt-3" variant="secondary" onClick={() => void detail.refetch()}>Try again</Button></Card>;
  const disabled = !!pending || stale || detail.isError || detail.isPaused;
  const activeReminder = data.reminders.find(row => row.state === "pending");
  const latestDelivered = data.reminders.find(row => row.state === "delivered");
  const reminderEnabled = state === "finished_plugged";

  async function run(action: string, task: () => Promise<unknown>, message: string) {
    setPending(action); setError(""); setSuccess("");
    try { await task(); delete requests.current[action]; await Promise.all([client.invalidateQueries({ queryKey: ["session-coordination", sessionId] }), client.invalidateQueries({ queryKey: ["charger"] }), client.invalidateQueries({ queryKey: ["unread"] })]); setSuccess(message); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not confirm the update. Please retry."); }
    finally { setPending(""); }
  }
  function schedule(snooze?: Reminder) {
    const action = snooze ? "snooze" : "reminder";
    const count = snooze ? 5 : Number(minutes);
    const serverNow = new Date(data!.server_time).getTime() + Math.max(0, Date.now() - detail.dataUpdatedAt);
    const request = requests.current[action] ?? { key: newRequestKey(), due: new Date(serverNow + count * 60000).toISOString() };
    requests.current[action] = request;
    return run(action, () => api(snooze ? `/reminders/${snooze.id}/snooze` : `/sessions/${sessionId}/reminders`, { method: "POST", body: { due_at: request.due, idempotency_key: request.key } }), snooze ? "Snoozed for five minutes." : "Return reminder saved.");
  }
  function saveDeparture(event: FormEvent) {
    event.preventDefault(); if (!expected) return;
    void run("departure", () => api(`/sessions/${sessionId}/departure`, { method: "PATCH", body: { expected_at: new Date(expected).toISOString() } }), "Expected departure saved.");
  }

  return <section className="grid gap-4 lg:grid-cols-2" aria-label="Your charging plans">
    {error ? <div className="lg:col-span-2"><ErrorPanel message={error} /></div> : null}
    {success ? <p role="status" className="rounded-lg bg-green-50 p-3 text-sm lg:col-span-2">{success}</p> : null}
    {detail.isError ? <div className="lg:col-span-2"><RefreshNotice failed updatedAt={detail.dataUpdatedAt} /></div> : null}
    <Card>
      <h2 className="text-lg font-semibold">Expected departure</h2>
      {data.departure ? <p className="mt-3 text-sm">Expected unplug: <strong>{stationTime(data.departure.expected_at, data.timezone)}</strong></p> : null}
      <form className="mt-4 flex min-w-0 flex-wrap items-end gap-3" onSubmit={saveDeparture}>
        <Field label="Unplug time (your device time)"><TextInput type="datetime-local" required value={expected} onChange={event => setExpected(event.target.value)} disabled={disabled} /></Field>
        <Button type="submit" disabled={disabled || !expected}>{pending === "departure" ? "Saving…" : "Share expected time"}</Button>
        {data.departure ? <Button variant="secondary" type="button" disabled={disabled} onClick={() => void run("clear-departure", () => api(`/sessions/${sessionId}/departure`, { method: "PATCH", body: { expected_at: null } }), "Departure cleared.")}>Clear report</Button> : null}
      </form>
      <details className="ev-details-note"><summary>Details</summary><p>Shared anonymously in {data.timezone}. Choose a future time within 24 hours. Your estimate expires and does not release your app slot.</p></details>
    </Card>
    <Card>
      <h2 className="text-lg font-semibold" id="return-reminder">Return reminder</h2>
      {data.waiting_count > 0 ? <p className="mt-2 text-sm text-primary">{data.waiting_count} {data.waiting_count === 1 ? "driver waiting" : "drivers waiting"}.</p> : null}
      {activeReminder ? <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-green-50 p-3"><p className="text-sm">Reminder set for <strong>{stationTime(activeReminder.due_at, data.timezone)}</strong></p><Button variant="secondary" disabled={disabled} onClick={() => void run("cancel-reminder", () => api(`/reminders/${activeReminder.id}`, { method: "DELETE" }), "Reminder cancelled.")}>Cancel reminder</Button></div> : latestDelivered ? <p className="mt-3 text-sm">Your reminder was delivered to Notifications.</p> : null}
      {reminderEnabled ? <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={event => { event.preventDefault(); void schedule(); }}>
        <Field label="Remind me in"><SelectInput value={minutes} disabled={disabled} onChange={event => { setMinutes(event.target.value); delete requests.current.reminder; }}>{[5, 10, 15, 30, 60].map(value => <option value={value} key={value}>{value} minutes</option>)}</SelectInput></Field>
        <Button type="submit" disabled={disabled}>{pending === "reminder" ? "Saving…" : activeReminder ? "Replace reminder" : "Set return reminder"}</Button>
        {activeReminder || latestDelivered ? <Button type="button" variant="secondary" disabled={disabled} onClick={() => void schedule(activeReminder ?? latestDelivered)}>Snooze for 5 minutes</Button> : null}
      </form> : <p className="mt-3 text-sm text-slate-500">Available after you report charging finished.</p>}
      <details className="ev-details-note"><summary>Details</summary><p>Saved in-app reminders work with your browser closed. No SMS or push delivery. Unplugging cancels pending reminders.</p></details>
    </Card>
  </section>;
}
