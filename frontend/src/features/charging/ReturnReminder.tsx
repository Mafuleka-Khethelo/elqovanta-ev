import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing } from "lucide-react";
import { api, ApiError } from "../../lib/api";
import { Button, ErrorPanel, Field, SelectInput } from "../../components/ui";
import { stationTime, useOffline } from "../coordination/Updates";
import type { DriverGuidance } from "../../lib/types";

type Reminder = { enabled: boolean; has_choice: boolean; lead_minutes: number; due_at: string | null; delivered_at: string | null; version: number; timezone: string; waiting_count: number };
export function ReturnReminder({ sessionId, guidance, hasEstimate, stale }: { sessionId: string; guidance?: DriverGuidance; hasEstimate: boolean; stale: boolean }) {
  const client = useQueryClient(), offline = useOffline();
  const query = useQuery({ queryKey: ["assistant-reminder", sessionId], queryFn: () => api<Reminder>(`/sessions/${sessionId}/assistant-reminder`), refetchInterval: () => document.visibilityState === "visible" ? 10000 : false });
  const [lead, setLead] = useState("10"), [editing, setEditing] = useState(false), [pending, setPending] = useState(false), [error, setError] = useState("");
  useEffect(() => { if (query.data && !editing) setLead(String(query.data.lead_minutes)); }, [query.data?.lead_minutes, editing]);
  const disabled = pending || offline || stale || query.isError || query.isPaused || !query.data;
  async function save(enabled: boolean) {
    setPending(true); setError("");
    try {
      const row = await api<Reminder>(`/sessions/${sessionId}/assistant-reminder`, { method: "PUT", body: { enabled, lead_minutes: Number(lead), expected_version: query.data?.version ?? 0 } });
      client.setQueryData(["assistant-reminder", sessionId], row); setEditing(false);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not update your return reminder."); void query.refetch(); }
    finally { setPending(false); }
  }
  const data = query.data;
  return <div className="mt-5 border-t border-slate-200 pt-4" id="assistant-return-reminder">
    <h3 className="flex items-center gap-2 font-semibold"><BellRing size={18} /> Return to your car</h3>
    {error ? <div className="mt-2"><ErrorPanel message={error} /></div> : null}
    {query.isError ? <p className="mt-2 text-sm text-amber-800">Your reminder could not be refreshed. Reconnect or refresh before changing it.</p> : null}
    <p className="mt-2 text-sm">{data?.enabled ? data.delivered_at ? "Your return reminder was sent. Check your notifications and your car." : <>Reminder enabled for <strong>{stationTime(data.due_at!, data.timezone)}</strong>. A saved battery update will move it with your estimated target.</> : data?.has_choice ? "Your optional return reminder is off. You can enable it whenever you need it." : guidance?.available && guidance.warning ? "The experimental advisory suggests planning your return. Would you like a reminder before your estimated target?" : "Would you like a reminder to return before your estimated charging target?"}</p>
    {hasEstimate ? <div className="mt-3 flex flex-wrap items-end gap-3">
      <Field label="Remind me before the target"><SelectInput value={lead} disabled={disabled} onChange={e => { setLead(e.target.value); setEditing(true); }}>{[5,10,15,20,30,60].map(n => <option key={n} value={n}>{n} minutes before</option>)}</SelectInput></Field>
      <Button type="button" disabled={disabled || (data?.enabled && !editing)} onClick={() => void save(true)}>{pending ? "Saving…" : data?.enabled ? "Update return reminder" : "Remind me to return"}</Button>
      <Button type="button" variant="secondary" disabled={disabled || (data?.has_choice && !data.enabled)} onClick={() => void save(false)}>{data?.enabled ? "Turn off return reminder" : "Not now"}</Button>
    </div> : <p className="mt-2 text-sm text-slate-500">Save a charging estimate to choose a reminder time.</p>}
    <p className="mt-3 text-xs text-slate-500">{data?.waiting_count ?? "—"} drivers waiting. The next turn follows your reported unplug. Reminders appear in the app and can be delayed while free hosting sleeps.</p>
  </div>;
}
