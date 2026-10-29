import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight } from "lucide-react";
import { api, ApiError, newRequestKey } from "../../lib/api";
import type { DriverGuidance, QueueView, Session } from "../../lib/types";
import { useOffline } from "./Updates";
import { ChargingWarningDialog, useChargingAdvisory } from "../chargers/ChargerGuidance";

export function NextActions({ session, queue, receivedAt, stale }: { session: Session | null | undefined; queue: QueueView | undefined; receivedAt: number; stale: boolean }) {
  const client = useQueryClient(), navigate = useNavigate();
  const offline = useOffline();
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");
  const [warning, setWarning] = useState<DriverGuidance | null>(null);
  const [checking, setChecking] = useState(false);
  const [now, setNow] = useState(Date.now());
  const keys = useRef<Record<string, string>>({});
  useEffect(() => { if (queue?.participation !== "offered") return; const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(timer); }, [queue?.participation]);
  const disabled = !!pending || checking || stale || offline;
  const seconds = queue?.offer_expires_at && queue.server_time ? Math.max(0, Math.floor((new Date(queue.offer_expires_at).getTime() - new Date(queue.server_time).getTime() - Math.max(0, now - receivedAt)) / 1000)) : 0;
  const chargerId = session?.charger_id ?? queue?.charger?.id;
  const advisory = useChargingAdvisory(chargerId ?? "", queue?.port_type, undefined, queue?.participation === "offered");

  async function act(name: string, task: (key: string) => Promise<unknown>) {
    setPending(name); setError("");
    const key = keys.current[name] ?? newRequestKey(); keys.current[name] = key;
    try { await task(key); delete keys.current[name]; await client.invalidateQueries(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not confirm the update. Please retry."); }
    finally { setPending(""); }
  }
  function action(name: string, label: string, path: string, primary = false) {
    return <button type="button" className={primary ? "ev-button ev-button-lime" : "ev-next-secondary"} disabled={disabled} onClick={() => void act(name, key => api(path, { method: "POST", body: { idempotency_key: key } }))}>{pending === name ? "Updating…" : label}{primary ? <ArrowUpRight size={17} /> : null}</button>;
  }
  function contact() {
    return act("message", async () => { const result = await api<{ id: string }>("/conversations", { method: "POST", body: { charger_id: chargerId } }); navigate(`/app/messages/${result.id}`); });
  }
  function accept() { setWarning(null); void act("accept", key => api("/queue/accept", { method: "POST", body: { idempotency_key: key } })); }
  async function reviewAccept() {
    setChecking(true);
    try { const result = await advisory.refetch(); if (result.data?.available && result.data.warning) setWarning(result.data); else accept(); }
    finally { setChecking(false); }
  }

  return <div className="ev-next-actions">
    {error ? <p role="alert" className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs leading-5 text-amber-950">{error}</p> : null}
    {session ? <>
      {(session.state === "charging" || session.state === "paused") ? action("finish", "Report charging finished", `/sessions/${session.id}/finish`, true) : action("unplug", "Report unplugged", `/sessions/${session.id}/unplug`, true)}
      <div className="ev-next-links">
        {session.state === "finished_plugged" ? <Link to="/app/session#return-reminder">Set a return reminder</Link> : null}
        <button type="button" disabled={disabled} onClick={() => void contact()}>Contact manager</button><Link to="/app/session">Session details</Link>
      </div>
    </> : queue?.participation === "offered" ? <>
      <button className="ev-button ev-button-lime" type="button" disabled={disabled || seconds === 0} onClick={() => void reviewAccept()}>{checking ? "Checking…" : pending === "accept" ? "Accepting…" : "Accept coordination offer"}<ArrowUpRight size={17} /></button>
      <p className="ev-offer-countdown" role="timer">{seconds > 0 ? `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s left to accept` : "Offer expired. Refresh your waiting list."}</p>
      <div className="ev-next-links"><button type="button" disabled={disabled} onClick={() => void act("leave", () => api("/queue/leave", { method: "POST" }))}>Decline offer</button><Link to="/app/queue">View waiting list</Link></div>
    </> : queue?.participation === "waiting" ? <>
      <Link className="ev-button ev-button-lime" to="/app/queue">View my waiting list<ArrowUpRight size={17} /></Link>
      <div className="ev-next-links"><Link to="/app/queue#alternatives">Compare alternatives</Link><button type="button" disabled={disabled} onClick={() => void act("leave", () => api("/queue/leave", { method: "POST" }))}>Leave waiting list</button></div>
    </> : queue?.participation === "session" ? <Link className="ev-button ev-button-lime" to="/app/session">Open my session<ArrowUpRight size={17} /></Link> : <>
      <Link className="ev-button ev-button-lime" to="/app/chargers">Find a charger<ArrowUpRight size={17} /></Link><div className="ev-next-links"><Link to="/app/favourites">Open saved chargers</Link></div>
    </>}
    <ChargingWarningDialog data={warning} pending={!!pending} blocked={stale || offline || checking || seconds === 0} onContinue={accept} onClose={() => setWarning(null)} />
  </div>;
}
