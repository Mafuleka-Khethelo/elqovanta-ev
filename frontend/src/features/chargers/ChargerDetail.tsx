import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api, newRequestKey } from "../../lib/api";
import type { ChargerDetail, DriverGuidance } from "../../lib/types";
import { statusLabel } from "../../lib/format";
import { Badge, Button, Card, ErrorPanel, PageHeader, Skeleton, SourceNote, statusTone } from "../../components/ui";
import { useToast } from "../../app/providers";
import { ChargingWarningDialog, useChargingAdvisory } from "./ChargerGuidance";
import { ArrivalPlanner } from "./ArrivalPlanner";
import { Alternatives } from "../coordination/Alternatives";
import { HelpReports } from "../coordination/HelpReports";
import { RefreshNotice, reportAge, stationTime, useOffline } from "../coordination/Updates";

export function ChargerDetailPage() {
  const { chargerId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const offline = useOffline();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [keys] = useState<Record<string, string>>({});
  const [portType, setPortType] = useState("");
  const [warning, setWarning] = useState<DriverGuidance | null>(null);
  const [checking, setChecking] = useState(false);
  const advisory = useChargingAdvisory(chargerId, portType || null);
  const charger = useQuery({
    queryKey: ["charger", chargerId],
    queryFn: () => api<ChargerDetail>(`/chargers/${chargerId}`),
    refetchInterval: () => (document.visibilityState === "visible" ? 8000 : false),
    refetchIntervalInBackground: false,
  });
  useEffect(() => { const ports = charger.data?.port_types ?? []; setPortType(ports.length === 1 ? ports[0].name : ""); }, [charger.data?.id]);

  function startCharging() {
    setWarning(null);
    void act("start", async key => {
      await api("/sessions", { method: "POST", body: { charger_id: chargerId, port_type: portType || null, idempotency_key: key } });
      toast("Charging session started."); navigate("/app/session");
    });
  }
  async function reviewStart() {
    setChecking(true);
    try { const result = await advisory.refetch(); if (result.data?.available && result.data.warning) setWarning(result.data); else startCharging(); }
    finally { setChecking(false); }
  }

  async function act(name: string, run: (key: string) => Promise<void>) {
    const key = keys[name] ?? newRequestKey();
    keys[name] = key;
    setPending(name);
    setError(null);
    try {
      await run(key);
      delete keys[name];
      await queryClient.invalidateQueries();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The request failed.");
    } finally {
      setPending(null);
    }
  }

  if (charger.isLoading) return <Skeleton className="h-64" />;
  if (!charger.data) return <ErrorPanel message="This charger could not be loaded. Refresh to try again." />;
  const item = charger.data;

  return (
    <div className="space-y-4">
      <PageHeader
        title={item.display_name}
      />
      {error ? <ErrorPanel message={error} /> : null}
      <RefreshNotice failed={(charger.isError || charger.isPaused || offline)} updatedAt={charger.dataUpdatedAt} />
      <ArrivalPlanner key={item.id} charger={item} portType={portType} onPortChange={setPortType} offline={offline} />
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={statusTone(item.app_status)}>{statusLabel(item.app_status)}</Badge>
          {item.coordination_enabled ? <Badge tone="teal">Queue open</Badge> : <Badge>Queue not available</Badge>}
        </div>
        <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <div><dt className="text-slate-500">App-reported status updated</dt><dd>{item.status_updated_at ? `${stationTime(item.status_updated_at, item.timezone)} (${item.timezone}) · ${reportAge(item.status_updated_at, item.server_time)}` : "Not reported"}</dd></div>
          <div><dt className="text-slate-500">Reported by</dt><dd>{item.status_source ?? "Not reported"}</dd></div>
          <div><dt className="text-slate-500">Observed port types</dt><dd>{item.port_types.length ? item.port_types.map((port) => port.name).join(", ") : "None listed"}</dd></div>
          <div><dt className="text-slate-500">Queue</dt><dd>{item.waiting_count} waiting · {item.active_session_count} connected</dd></div>
          <div><dt className="text-slate-500">Station manager</dt><dd>{item.manager_names.length ? item.manager_names.join(", ") : "None assigned yet"}</dd></div>
          {item.coordinates_on_map ? null : <div><dt className="text-slate-500">Map</dt><dd>Not shown on the map.</dd></div>}
        </dl>
      </Card>
      {item.departure_reports.length ? <Card><h2 className="font-semibold">Participating drivers’ expected departures</h2><ul className="mt-3 space-y-2 text-sm leading-6">{item.departure_reports.map((report,index)=><li key={`${report.reported_at}-${index}`}>A participating driver expects to unplug around <strong>{stationTime(report.expected_at,item.timezone)}</strong> ({item.timezone}) — reported {reportAge(report.reported_at,item.server_time)}.</li>)}</ul><p className="mt-3 text-xs leading-5 text-slate-500">These anonymous, voluntary reports expire. They do not guarantee a vacant bay or when you will receive an offer.</p></Card> : null}
      {item.your_queue_state ? <SourceNote>
        {item.your_queue_state === "waiting"
          ? `You are waiting here, in position ${item.your_queue_position ?? "—"}.`
          : item.your_queue_state === "offered"
            ? "A place is ready for you."
            : "You can wait at one charger at a time."}
      </SourceNote> : null}
      <div className="ev-station-actions"><h2>At the station now?</h2><span>Starting or joining the waiting list uses now, not your planned arrival.</span></div>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          disabled={pending !== null || (charger.isError || charger.isPaused || offline)}
          onClick={() => void act("favourite", async (key) => {
            if (item.is_favourite) await api(`/favourites/${item.id}`, { method: "DELETE" });
            else await api("/favourites", { method: "POST", body: { charger_id: item.id, idempotency_key: key } });
            toast(item.is_favourite ? "Removed from favourites." : "Saved to favourites.");
          })}
        >
          {item.is_favourite ? "Remove favourite" : "Save favourite"}
        </Button>
        <Button variant="secondary" disabled={pending !== null || (charger.isError || charger.isPaused || offline)} onClick={() => void act("message", async () => {
          const created = await api<{ id: string }>("/conversations", { method: "POST", body: { charger_id: item.id } });
          navigate(`/app/messages/${created.id}`);
        })}>
          Message the manager
        </Button>
        <Button disabled={checking || pending !== null || (item.port_types.length > 1 && !portType) || (charger.isError || charger.isPaused || offline) || !item.coordination_enabled || item.app_status === "offline" || item.app_status === "paused"} onClick={() => void act("join", async (key) => {
          await api("/queue/join", { method: "POST", body: { charger_id: item.id, port_type: portType || null, idempotency_key: key } });
          toast("You joined the waiting list.");
          navigate("/app/queue");
        })}>
          Join waiting list
        </Button>
        <Button variant="secondary" disabled={checking || pending !== null || (item.port_types.length > 1 && !portType) || (charger.isError || charger.isPaused || offline) || !item.coordination_enabled || item.app_status === "offline" || item.app_status === "paused"} onClick={() => void reviewStart()}>
          {checking ? "Checking…" : "Start charging"}
        </Button>
      </div>
      {!item.coordination_enabled ? <SourceNote>The waiting list is closed.</SourceNote> : null}
      <details className="ev-details-note"><summary>About status and queues</summary><p>Status is reported by drivers and managers. An app offer does not reserve a physical bay.</p></details>
      <Alternatives chargerId={item.id} />
      <HelpReports chargerId={item.id} />
      <ChargingWarningDialog data={warning} pending={pending !== null} blocked={charger.isError || charger.isPaused || offline} onContinue={startCharging} onClose={() => setWarning(null)} />
    </div>
  );
}
