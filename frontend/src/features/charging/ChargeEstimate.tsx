import { useEffect, useRef, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api, newRequestKey } from "../../lib/api";
import type { ChargeEstimate, ChargePlan, Vehicle } from "../../lib/types";
import { Button, Card, ErrorPanel, Field, SelectInput, TextInput } from "../../components/ui";
import { stationTime, useOffline } from "../coordination/Updates";

type EstimateResponse = { estimate: ChargeEstimate | null; version: number; server_time: string; timezone: string };
const empty = { vehicle_id: "", vehicle_label: "My vehicle", battery_capacity_kwh: "", current_percent: "", target_percent: "80", average_power_kw: "", charging_kind: "AC" as "AC" | "DC" };
export function ChargingEstimate({ sessionId, state = "charging", timezone = "UTC", onPlanChange, vehicleId, initialPlan }: {
  sessionId?: string; state?: string; timezone?: string; onPlanChange?: (value: ChargePlan | null, dirty: boolean) => void;
  vehicleId?: string; initialPlan?: ChargePlan | null;
}) {
  const client = useQueryClient();
  const offline = useOffline();
  const vehicles = useQuery({ queryKey: ["vehicles"], queryFn: () => api<Vehicle[]>("/me/vehicles") });
  const saved = useQuery({ queryKey: ["charge-estimate", sessionId], queryFn: () => api<EstimateResponse>(`/sessions/${sessionId}/charge-estimate`), enabled: !!sessionId,
    refetchInterval: () => document.visibilityState === "visible" ? 10000 : false, refetchIntervalInBackground: false });
  const [draft, setDraft] = useState(empty);
  const [open, setOpen] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [preview, setPreview] = useState<{ estimate: ChargeEstimate; server_time: string; received: number } | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(Date.now());
  const key = useRef<string | null>(null);
  const initialized = useRef<string | null>(null);
  const preparedVehicle = useRef<string | null>(null);
  useEffect(() => {
    if (sessionId || !vehicleId || !vehicles.data || preparedVehicle.current === vehicleId) return;
    const v = vehicles.data.find(item => item.id === vehicleId);
    if (!v) return;
    preparedVehicle.current = vehicleId;
    const previous = initialPlan?.vehicle_id === vehicleId ? initialPlan : null;
    setDraft({ ...empty, vehicle_id: v.id, vehicle_label: v.model_name || v.nickname,
      battery_capacity_kwh: v.battery_capacity_kwh ? String(v.battery_capacity_kwh) : "",
      target_percent: previous ? String(previous.target_percent) : "80",
      average_power_kw: previous ? String(previous.average_power_kw) : "", charging_kind: previous?.charging_kind ?? "AC" });
    setPreview(null); setDirty(true); setOpen(true); key.current = null; onPlanChange?.(null, true);
  }, [vehicleId, vehicles.data, sessionId, initialPlan, onPlanChange]);
  useEffect(() => { const timer = window.setInterval(() => setTick(Date.now()), 1000); return () => window.clearInterval(timer); }, []);
  const current = sessionId ? saved.data?.estimate : preview?.estimate;
  useEffect(() => {
    const row = saved.data?.estimate;
    if (!row || row.id === initialized.current || dirty) return;
    initialized.current = row.id ?? null;
    setDraft({ vehicle_id: row.vehicle_id ?? "", vehicle_label: row.vehicle_label, battery_capacity_kwh: String(row.battery_capacity_kwh), current_percent: "",
      target_percent: String(row.target_percent), average_power_kw: String(row.average_power_kw), charging_kind: row.charging_kind });
    setOpen(false);
  }, [saved.data?.estimate, dirty]);
  const blocked = offline || pending || !!(sessionId && (saved.isError || saved.isPaused));
  const vehicle = vehicles.data?.find(v => v.id === draft.vehicle_id);
  function change(name: keyof typeof empty, value: string) {
    setDraft(previous => ({ ...previous, [name]: value })); setDirty(true); setPreview(null); key.current = null; onPlanChange?.(null, true);
  }
  function chooseVehicle(id: string) {
    const v = vehicles.data?.find(item => item.id === id);
    setDraft(previous => ({ ...previous, vehicle_id: id, vehicle_label: v?.model_name || v?.nickname || "My vehicle", battery_capacity_kwh: v?.battery_capacity_kwh ? String(v.battery_capacity_kwh) : "" }));
    setDirty(true); setPreview(null); key.current = null; onPlanChange?.(null, true);
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); setPending(true); setError("");
    const body: ChargePlan = { vehicle_id: draft.vehicle_id || null, vehicle_label: draft.vehicle_label,
      battery_capacity_kwh: Number(draft.battery_capacity_kwh), current_percent: Number(draft.current_percent), target_percent: Number(draft.target_percent),
      average_power_kw: Number(draft.average_power_kw), charging_kind: draft.charging_kind };
    try {
      key.current ??= newRequestKey();
      const result = await api<{ estimate: ChargeEstimate; server_time: string }>(sessionId ? `/sessions/${sessionId}/charge-estimate` : "/charging-estimates/preview",
        { method: "POST", body: sessionId ? { ...body, expected_version: saved.data?.version ?? 0, idempotency_key: key.current } : body });
      setDirty(false); key.current = null;
      if (sessionId) await Promise.all([client.invalidateQueries({ queryKey: ["charge-estimate", sessionId] }), client.invalidateQueries({ queryKey: ["station-estimates"] })]);
      else { setPreview({ ...result, received: Date.now() }); onPlanChange?.(body, false); }
      setOpen(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not calculate the charging time.");
      if (sessionId) void client.invalidateQueries({ queryKey: ["charge-estimate", sessionId] });
    } finally { setPending(false); }
  }
  async function clear() {
    setError(""); setPending(true);
    try {
      if (sessionId && current?.version) await api(`/sessions/${sessionId}/charge-estimate?version=${current.version}`, { method: "DELETE" });
      setPreview(null); setDraft(empty); setDirty(false); key.current = null; onPlanChange?.(null, false); setOpen(true);
      if (sessionId) await Promise.all([client.invalidateQueries({ queryKey: ["charge-estimate", sessionId] }), client.invalidateQueries({ queryKey: ["station-estimates"] })]);
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not remove the estimate."); }
    finally { setPending(false); }
  }
  const serverTime = sessionId ? saved.data?.server_time : preview?.server_time;
  const received = sessionId ? saved.dataUpdatedAt : preview?.received;
  const now = serverTime ? Date.parse(serverTime) + Math.max(0, tick - (received ?? tick)) : tick;
  const seconds = current ? sessionId ? Math.max(0, Math.ceil((Date.parse(current.estimated_target_at) - now) / 1000)) : current.duration_seconds : 0;
  const minutes = Math.ceil(seconds / 60);
  const duration = minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes}m`;
  const zone = sessionId ? saved.data?.timezone || timezone : timezone;
  const percent = current ? Math.min(current.target_percent, current.current_percent + Math.max(0, now - Date.parse(current.anchor_at)) / 3600000 * current.effective_power_kw / current.battery_capacity_kwh * 100) : 0;
  if (sessionId && state !== "charging") return current ? <Card><h2 className="font-semibold">Charging estimate</h2><p className="mt-2 text-sm">Charging is no longer reported as active. Estimated-time alerts have stopped.</p></Card> : null;
  return <Card>
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">{sessionId ? "Your charging target" : "Plan this charge before starting"}</h2><p className="mt-1 text-xs text-slate-500">{sessionId ? "Car-specific calculation · no live battery connection" : "Vehicle → battery levels → estimated time → plug in and start"}</p></div>
      {sessionId || current ? <Button type="button" variant="secondary" disabled={pending} onClick={() => setOpen(!open)}>{open ? "Hide details" : sessionId ? "Update battery reading" : "Edit charging plan"}</Button> : null}</div>
    {error ? <div className="mt-3"><ErrorPanel message={error} /></div> : null}
    {sessionId && saved.isError ? <p className="mt-3 text-sm text-amber-800">Estimate updates unavailable. Changes are disabled until refreshed.</p> : null}
    {current ? <div className="mt-4 rounded-xl border border-[#cbded0] bg-[#f1f6ef] p-4" aria-live="polite">
      <p className="mb-3 text-sm font-semibold">{current.vehicle_label}</p>
      <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-primary">Estimated {current.target_percent}% target</p><p className="mt-1 text-xl font-semibold">{stationTime(current.estimated_target_at, zone)}</p><p className="text-xs text-slate-500">{zone}{!sessionId ? " · If charging starts at the preview time" : ""}</p></div><strong className="text-xl text-primary">{seconds > 0 ? `About ${duration}${sessionId ? " left" : " charging"}` : sessionId ? "Check your car" : "Target already reached"}</strong></div>
      {sessionId ? <><progress className="mt-4 h-3 w-full accent-[#24645d]" max={100} value={percent} aria-label="Calculated battery estimate" /><p className="mt-1 text-xs text-slate-600">Calculated estimate: {percent.toFixed(1)}% · last entered reading: {current.current_percent}%</p></> : null}
      <p className="mt-3 text-sm">{seconds === 0 ? "Estimated target time reached. Confirm charging finished or enter a newer battery reading; this does not confirm the battery is full." : `${current.energy_needed_kwh} kWh needed, assuming ${current.effective_power_kw} kW average reaches the battery.`}</p>
      <p className="mt-2 text-sm font-medium text-primary">{sessionId ? "Automatic in-app reminders are scheduled for 10 minutes before the estimated target and at the target time." : "Automatic in-app reminders will be scheduled for 10 minutes before the estimated target and at the target time when you start."}</p>
      <p className="mt-2 text-xs text-slate-600">{sessionId ? "Waiting drivers receive anonymous estimated-time notices. Unplugging controls the next offer." : "Your session clock has not started. The finish time is recalculated from your actual start. Waiting may shift it."}</p>
      <details className="ev-details-note"><summary>Calculation assumptions</summary><p>{current.assumption} Charging toward 100% may slow substantially. Use usable battery capacity and an expected average, not a guaranteed peak rate.</p></details>
    </div> : sessionId ? <p className="mt-3 text-sm text-slate-600">Enter your current battery reading to estimate a target time and enable in-app notices.</p> : null}
    {open ? <form className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={event => void submit(event)}>
      {sessionId ? <Field label="Your vehicle"><SelectInput value={draft.vehicle_id} onChange={e => chooseVehicle(e.target.value)} disabled={blocked}><option value="">Enter details for this charge</option>{vehicles.data?.map(v => <option key={v.id} value={v.id}>{v.nickname}{v.model_name ? ` · ${v.model_name}` : ""}</option>)}</SelectInput></Field> : <div className="rounded-lg bg-slate-50 p-3 text-sm"><span className="text-slate-500">Selected vehicle</span><p className="font-semibold">{vehicle?.nickname || "Choose your vehicle above"}</p><p className="text-xs text-slate-500">{vehicle?.model_name}</p></div>}
      {!draft.vehicle_id ? <Field label="Car model / version"><TextInput value={draft.vehicle_label} maxLength={140} required disabled={blocked} onChange={e => change("vehicle_label", e.target.value)} /></Field> : null}
      <Field label="Usable battery capacity (kWh)"><TextInput type="number" step="0.1" min="0.1" max="500" required value={draft.battery_capacity_kwh} readOnly={!!vehicle?.battery_capacity_kwh} disabled={blocked} onChange={e => change("battery_capacity_kwh", e.target.value)} /></Field>
      <Field label="Current battery reading (%)"><TextInput type="number" step="0.1" min="0" max="100" required value={draft.current_percent} disabled={blocked} onChange={e => change("current_percent", e.target.value)} /></Field>
      <Field label="Target battery (%)"><TextInput type="number" step="0.1" min="0.1" max="100" required value={draft.target_percent} disabled={blocked} onChange={e => change("target_percent", e.target.value)} /></Field>
      <Field label="Charging type"><SelectInput value={draft.charging_kind} disabled={blocked} onChange={e => change("charging_kind", e.target.value)}><option value="AC">AC</option><option value="DC">DC</option></SelectInput></Field>
      <Field label="Assumed average power into battery (kW)" hint="Charger power is not recorded here. Enter an expected average; a peak rating is not a guaranteed average."><TextInput type="number" step="0.1" min="0.1" max="1000" required value={draft.average_power_kw} disabled={blocked} onChange={e => change("average_power_kw", e.target.value)} /></Field>
      <div className="flex flex-wrap gap-2 sm:col-span-2 lg:col-span-3"><Button type="submit" disabled={blocked || (!!sessionId && saved.isLoading)}>{pending ? "Calculating…" : sessionId ? "Save charging estimate" : "Calculate charging time"}</Button><Button type="button" variant="secondary" disabled={blocked} onClick={() => void clear()}>{sessionId && current ? "Remove estimate" : "Clear details"}</Button></div>
      {dirty && !sessionId ? <p className="text-xs text-slate-500 sm:col-span-2 lg:col-span-3">Review the calculated time before joining the queue or starting. No timer runs yet.</p> : null}
    </form> : null}
  </Card>;
}

type Shared = { items: { stage: string; estimated_target_at: string | null; is_estimate: boolean }[]; connected_count: number; unestimated_count: number; server_time: string; timezone: string; notice: string };
export function StationChargingEstimates({ chargerId }: { chargerId: string }) {
  const data = useQuery({ queryKey: ["station-estimates", chargerId], queryFn: () => api<Shared>(`/chargers/${chargerId}/charging-estimates`),
    refetchInterval: () => document.visibilityState === "visible" ? 10000 : false, refetchIntervalInBackground: false });
  if (!data.data || data.data.connected_count === 0) return data.isError ? <p className="text-sm text-slate-500">Charging estimates could not be refreshed.</p> : null;
  const value = data.data;
  return <Card><h2 className="font-semibold">Charging progress at this station</h2>
    <ul className="mt-3 space-y-2 text-sm">{value.items.map((item, index) => <li key={`${item.estimated_target_at}-${item.stage}-${index}`} className="rounded-lg bg-slate-50 p-3">{item.stage === "driver_reported_finished" ? "A driver reported charging finished and is still connected." : item.stage === "estimated_target_time_passed" ? "A session's estimated target time has passed. Completion has not been confirmed." : <>A session is estimated to reach its charging target around <strong>{stationTime(item.estimated_target_at!, value.timezone)}</strong> ({value.timezone}).</>}</li>)}</ul>
    {value.unestimated_count > 0 ? <p className="mt-3 text-sm text-slate-500">{value.unestimated_count} connected {value.unestimated_count === 1 ? "session has" : "sessions have"} no current charging-time estimate.</p> : null}
    <p className="mt-3 text-xs text-slate-500">{value.notice}</p>{data.isError ? <p className="mt-2 text-xs text-amber-800">Last loaded estimates shown; updates unavailable.</p> : null}
  </Card>;
}
