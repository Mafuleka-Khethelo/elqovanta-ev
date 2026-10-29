import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api, newRequestKey } from "../../lib/api";
import type { ChargePlan, DriverGuidance, QueueView } from "../../lib/types";
import { statusLabel } from "../../lib/format";
import { Button, Card, EmptyState, ErrorPanel, PageHeader } from "../../components/ui";
import { Alternatives } from "../coordination/Alternatives";
import { RefreshNotice, useOffline } from "../coordination/Updates";
import { ChargingEstimate, StationChargingEstimates } from "../charging/ChargeEstimate";
import { VehicleChoice, useVehicleSelection } from "../vehicles/VehicleChoice";
import { DepartureNotice } from "../coordination/DepartureNotice";
import { ChargingWarningDialog, useChargingAdvisory } from "../chargers/ChargerGuidance";

export function QueuePage() {
  const navigate = useNavigate(), vehicle = useVehicleSelection();
  const [plan, setPlan] = useState<ChargePlan | null>(null);
  const [dirty, setDirty] = useState(true), [plugged, setPlugged] = useState(false);
  const queryClient = useQueryClient();
  const offline = useOffline();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());
  const [offset, setOffset] = useState(0);
  const [acceptKey, setAcceptKey] = useState(() => newRequestKey());
  const [warning, setWarning] = useState<DriverGuidance | null>(null);
  const [checking, setChecking] = useState(false);
  const queue = useQuery({
    queryKey: ["queue"],
    queryFn: () => api<QueueView>("/queue"),
    refetchInterval: () => (document.visibilityState === "visible" ? 5000 : false),
    refetchIntervalInBackground: false,
  });
  const advisory = useChargingAdvisory(queue.data?.charger?.id ?? "", queue.data?.port_type, undefined, queue.data?.participation === "offered");
  const planReady = !!plan && !dirty && plan.vehicle_id === vehicle.selected?.id;
  function accept() { if (!planReady || !plugged) return; setWarning(null); void run("accept", async () => { await api("/queue/accept", { method: "POST", body: { idempotency_key: acceptKey, charge_estimate: plan } }); setAcceptKey(newRequestKey()); navigate("/app/session"); }); }
  async function reviewAccept() { if (!planReady || !plugged) return; setChecking(true); try { const result = await advisory.refetch(); if (result.data?.available && result.data.warning) setWarning(result.data); else accept(); } finally { setChecking(false); } }

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (queue.data?.server_time) setOffset(new Date(queue.data.server_time).getTime() - Date.now());
  }, [queue.data?.server_time]);

  async function run(name: string, action: () => Promise<void>) {
    setPending(name);
    setError(null);
    try {
      await action();
      await queryClient.invalidateQueries({ queryKey: ["queue"] });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The request failed.");
    } finally {
      setPending(null);
    }
  }

  const data = queue.data;
  const remaining = data?.offer_expires_at
    ? Math.max(0, Math.floor((new Date(data.offer_expires_at).getTime() - (now + offset)) / 1000))
    : null;

  return (
    <div className="space-y-4">
      <PageHeader
        title="My waiting list"
      />
      {error ? <ErrorPanel message={error} /> : null}
      <RefreshNotice failed={(queue.isError || queue.isPaused || offline)} updatedAt={queue.dataUpdatedAt} />
      {(!data && !(queue.isError || queue.isPaused || offline)) || data?.participation === "none" ? (
        <EmptyState title="You are not waiting" message="Join from a charger page." action={<Link className="font-semibold text-primary" to="/app/chargers">Find chargers</Link>} />
      ) : null}
      {data && data.participation === "session" ? (
        <Card>
          <p className="font-semibold">You already have an open session{data.charger ? ` at ${data.charger.display_name}` : ""}.</p>
          <p className="mt-2 text-sm text-slate-600">Report that you have unplugged before joining a waiting list somewhere else.</p>
          <Link className="mt-3 inline-block font-semibold text-primary" to="/app/session">Go to my session</Link>
        </Card>
      ) : null}
      {data && (data.participation === "waiting" || data.participation === "offered") ? (
        <Card>
          <h2 className="text-lg font-semibold">{data.charger?.display_name}</h2>
          <p className="text-sm text-slate-500">{data.charger ? statusLabel(data.charger.app_status) : "Not reported"}</p>
          {data.participation === "waiting" ? (
            <p className="mt-3">Your position is {data.position} of {data.waiting_count} waiting.</p>
          ) : (
            <div className="mt-3">
              <p className="font-semibold">A place is ready for you.</p>
              <p className="text-sm text-slate-600">{remaining ?? 0} seconds left to accept.</p>
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            {data.participation === "offered" ? (
              <a href="#offer-plan" className="rounded-lg bg-[#24645d] px-4 py-2 text-sm font-semibold text-white">Review your charge below</a>
            ) : null}
            <Button variant="secondary" disabled={pending !== null || (queue.isError || queue.isPaused || offline)} onClick={() => void run("leave", () => api("/queue/leave", { method: "POST" }))}>Leave waiting list</Button>
            {data.charger ? (
              <Button variant="ghost" disabled={pending !== null || (queue.isError || queue.isPaused || offline)} onClick={() => void run("remind", () => api("/queue/remind", { method: "POST", body: { charger_id: data.charger?.id, idempotency_key: newRequestKey() } }))}>
                Send a polite reminder
              </Button>
            ) : null}
          </div>
        </Card>
      ) : null}
      {data?.participation === "waiting" && data.charge_plan ? <Card><h2 className="font-semibold">Your planned charge</h2><p className="mt-2 text-sm">{data.charge_plan.vehicle_label} · {data.charge_plan.current_percent}% → {data.charge_plan.target_percent}%</p><p className="mt-1 text-xs text-slate-500">Provisional until your turn. Confirm your latest battery reading when an offer arrives; your session clock has not started.</p></Card> : null}
      {data?.participation === "offered" ? <section id="offer-plan" className="space-y-4"><VehicleChoice />{vehicle.selected ? <ChargingEstimate key={`offer-${data.charger?.id}-${vehicle.selected.id}`} vehicleId={vehicle.selected.id} initialPlan={data.charge_plan} timezone={data.charger?.timezone} onPlanChange={(value, changed) => { setPlan(value); setDirty(changed); setPlugged(false); setAcceptKey(newRequestKey()); }} /> : null}{planReady ? <label className="flex items-center gap-3 rounded-xl border border-[#cbded0] bg-[#f3f8ef] p-4 text-sm"><input type="checkbox" checked={plugged} onChange={e => setPlugged(e.target.checked)} className="h-4 w-4 accent-[#24645d]" />I am plugged in and ready to start charging</label> : <p className="text-sm text-primary">Confirm your current battery reading and calculate the time before accepting.</p>}<Button disabled={!planReady || !plugged || remaining === 0 || checking || pending !== null || queue.isError || queue.isPaused || offline} onClick={() => void reviewAccept()}>{checking ? "Checking…" : "Accept offer and start charging"}</Button></section> : null}
      {data?.charger && (data.participation === "waiting" || data.participation === "offered") ? <><StationChargingEstimates chargerId={data.charger.id} /><DepartureNotice chargerId={data.charger.id} /><Alternatives key={data.charger.id} chargerId={data.charger.id} initiallyOpen /></> : null}
      <ChargingWarningDialog data={warning} pending={pending !== null} blocked={!planReady || !plugged || checking || queue.isError || queue.isPaused || offline || remaining === 0} onContinue={accept} onClose={() => setWarning(null)} />
    </div>
  );
}
