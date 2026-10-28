import { useQuery } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { formatWhen } from "../../lib/format";

function subscribeConnection(update: () => void) {
  window.addEventListener("online", update);
  window.addEventListener("offline", update);
  return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
}

export function useOffline() {
  return useSyncExternalStore(subscribeConnection, () => !navigator.onLine, () => false);
}

export function stationTime(value: string, timezone: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short", timeZone: timezone }).format(new Date(value));
}

export function reportAge(value: string, serverTime?: string) {
  const minutes = Math.max(0, Math.floor(((serverTime ? new Date(serverTime).getTime() : Date.now()) - new Date(value).getTime()) / 60000));
  return minutes < 1 ? "less than a minute ago" : minutes < 60 ? `${minutes} minutes ago` : minutes < 1440 ? `${Math.floor(minutes / 60)} hours ago` : `${Math.floor(minutes / 1440)} days ago`;
}

export function RefreshNotice({ failed, updatedAt }: { failed: boolean; updatedAt: number }) {
  const offline = useOffline();
  const unavailable = failed || offline;
  return <div role={unavailable ? "alert" : "status"} title="App refresh time. The station's reported status has its own timestamp." className={`text-xs leading-5 ${unavailable ? "rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-amber-950" : "text-slate-500"}`}>{unavailable ? "Updates unavailable · Last loaded: " : "Updated "}{updatedAt > 0 ? formatWhen(new Date(updatedAt).toISOString()) : "Waiting for an update"}</div>;
}

export function DemoBanner() {
  const context = useQuery({ queryKey: ["driver-demonstration"], queryFn: () => api<{active: boolean; charger_id?: string; charger_name?: string; historical_arrival_local?: string; timezone?: string}>("/demonstration/context"), refetchInterval: () => document.visibilityState === "visible" ? 15000 : false, refetchIntervalInBackground: false });
  if (!context.data?.active) return null;
  const data = context.data;
  return <aside className="mx-5 mt-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-950" aria-label="Historical demonstration"><strong>Historical demonstration · {data.historical_arrival_local?.replace("T", " ")} · {data.timezone}</strong><p>An examiner selected this historical example. Session reports and queue actions still use the actual current time.</p><Link className="font-semibold underline underline-offset-4" to={`/app/chargers/${data.charger_id}`}>Open demonstration charger: {data.charger_name}</Link>{context.isError ? <p role="alert">The demonstration context could not be refreshed.</p> : null}</aside>;
}
