import { CheckCircle2, Info, TriangleAlert } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { DriverGuidance } from "../../lib/types";
import { Button, Dialog } from "../../components/ui";

export function useChargingAdvisory(chargerId: string, portType?: string | null, sessionId?: string, enabled = true, plannedArrival?: string) {
  const params = new URLSearchParams();
  if (portType) params.set("port_type", portType);
  if (plannedArrival) params.set("planned_arrival", plannedArrival);
  return useQuery({
    queryKey: ["charging-advisory", chargerId, portType ?? "", sessionId ?? "", plannedArrival ?? ""],
    queryFn: ({ signal }) => api<DriverGuidance>(sessionId ? `/sessions/${sessionId}/guidance` : `/chargers/${chargerId}/guidance?${params}`, { signal }),
    enabled: !!chargerId && enabled,
    staleTime: 15000,
    refetchInterval: () => !sessionId && !plannedArrival && document.visibilityState === "visible" ? 60000 : false,
    refetchIntervalInBackground: false,
    retry: false,
  });
}

export function AdvisoryDetails({ data }: { data: DriverGuidance }) {
  const fallback = data.reason === "unavailable" ? "The model could not be checked right now. Charging and reminders remain available." : data.reason === "choose_port" ? "Choose a listed port type for an automatic advisory. No examiner selection is needed." : "The saved model does not cover this charger or selected port. Charging and reminders remain available.";
  return <details className="ev-details-note"><summary><Info size={13} />Details</summary><p>{data.explanation ?? fallback}</p>{data.arrival_local ? <p>Model arrival: {data.arrival_local.replace("T", " ")} · {data.timezone} · {data.port_type}</p> : null}</details>;
}

export function AdvisoryResult({ data, loading, error, session = false }: { data?: DriverGuidance; loading?: boolean; error?: string; session?: boolean }) {
  if (error) return <aside className="ev-charging-advisory is-unavailable" role="status"><Info size={21} /><div><span className="ev-advisory-label">Charging advisory</span><strong>Advisory unavailable</strong><span className="ev-advisory-copy">{error}</span></div></aside>;
  if (!data) return <aside className="ev-charging-advisory" role="status" aria-busy={loading}><Info size={21} /><div><span className="ev-advisory-label">Charging advisory</span><strong>{loading ? "Checking your arrival…" : "Choose your arrival"}</strong></div></aside>;
  if (!data.available) return <aside className="ev-charging-advisory is-unavailable" role="status"><Info size={21} /><div><span className="ev-advisory-label">Charging advisory</span><strong>{data.reason === "choose_port" ? "Choose a port to see your advisory" : "Advisory unavailable"}</strong><span className="ev-advisory-copy">{data.reason === "choose_port" ? "Your result appears automatically after choosing a supported port." : data.reason === "unavailable" ? "We could not check the model right now. Charging and reminders remain available." : "This charger or port is not covered. Charging and reminders remain available."}</span><AdvisoryDetails data={data} /></div></aside>;
  const warning = data.warning === true;
  const arrival = data.arrival_station ?? data.arrival_local;
  const zone = data.station_timezone ?? data.timezone;
  const when = arrival ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short", timeZone: zone }).format(new Date(arrival)) : null;
  return <aside className={`ev-charging-advisory${warning ? " is-warning" : ""}`} role="status" aria-label="Charging advisory" aria-busy={loading}>
    {warning ? <TriangleAlert size={22} /> : <CheckCircle2 size={22} />}
    <div><div className="ev-advisory-heading"><span className="ev-advisory-label">Charging advisory</span><span className="ev-experimental-badge">Experimental</span></div>
      <strong>{data.suggestion}</strong>
      <span className="ev-advisory-copy">{warning ? "More than 30 minutes connected without charging may occur. You can choose an optional return reminder in the Charging Assistant." : "You can still choose an optional return reminder while charging."}</span>
      {when ? <span className="ev-advisory-context">{session ? "Session arrival" : data.mode === "experimental_planned" ? "Planned arrival" : "Arriving now"}: {when} · {zone}{data.port_type ? ` · ${data.port_type}` : ""}</span> : null}
      <span className="ev-advisory-limit">Historical model · current conditions have not been validated.</span>
      {loading ? <span className="ev-advisory-context">Updating…</span> : null}
      <AdvisoryDetails data={data} />
    </div>
  </aside>;
}

export function ChargerGuidance({ chargerId, portType, sessionId }: { chargerId: string; portType?: string | null; sessionId?: string }) {
  const guidance = useChargingAdvisory(chargerId, portType, sessionId);
  return <AdvisoryResult data={guidance.data} loading={guidance.isFetching} error={guidance.isError ? "We could not refresh this advisory. Charging and reminders remain available." : undefined} session={!!sessionId} />;
}

export function ChargingWarningDialog({ data, pending, blocked, onContinue, onClose }: { data: DriverGuidance | null; pending?: boolean; blocked?: boolean; onContinue: () => void; onClose: () => void }) {
  return <Dialog title="Plan your return to the car" open={!!data} onClose={() => { if (!pending) onClose(); }}>
    <p className="text-sm leading-6">The model flags possible long periods connected without charging. If you continue, the Charging Assistant lets you choose a reminder before your estimated target. It stays off until you enable it.</p>
    <p className="mt-2 text-xs text-amber-900">Experimental · historical model · current conditions have not been validated.</p>
    {data ? <AdvisoryDetails data={data} /> : null}
    <div className="mt-5 flex flex-wrap gap-3"><Button disabled={pending || blocked} onClick={onContinue}>Continue anyway</Button><Button variant="secondary" disabled={pending} onClick={onClose}>Go back</Button></div>
  </Dialog>;
}
