import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight, Car, Clock3, Heart, MessageSquare, RefreshCw, Search, Users } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../../lib/api";
import { formatDuration, formatWhen, stateLabel } from "../../lib/format";
import { Badge, Button, Card, EmptyState, ErrorPanel, Field, Pagination, SelectInput, Skeleton, TextInput } from "../../components/ui";
import "./drivers.css";

type Totals = { sessions: number; completed: number; connected_seconds: number; charging_seconds: number; noncharging_seconds: number; last_session_at: string | null };
type Driver = { id: string; display_name: string; email: string; created_at: string; is_demonstration: boolean; activity_state: string; vehicle_count: number; favourite_count: number; open_reports: number; unread_messages: number; session_summary: Totals };
type Directory = { items: Driver[]; total: number; limit: number; offset: number; server_time: string; summary: Record<string, number>; chargers: {id: string; display_name: string}[] };
type Station = { charger_id: string; charger_name: string; can_manage: boolean };
type DriverDetail = {
  driver: Pick<Driver, "id" | "display_name" | "email" | "created_at" | "is_demonstration">;
  session_summary: Totals | null;
  vehicles: { id: string; nickname: string; model_name: string | null; battery_capacity_kwh: number | null; max_ac_kw: number | null; max_dc_kw: number | null }[];
  sessions: {total: number; limit: number; offset: number; items: (Station & { id: string; state: string; port_type: string | null; plugged_in_at: string; unplugged_at: string | null; connected_seconds: number; charging_seconds: number; noncharging_seconds: number; is_demonstration: boolean;
    estimate: { vehicle_label: string; current_percent: number; target_percent: number; estimated_target_at: string } | null;
    reminder: { enabled: boolean; due_at: string | null; delivered_at: string | null } | null })[]};
  queue: (Station & {state: string; joined_at: string; offer_expires_at: string | null}) | null;
  favourites: { total: number; items: Station[] };
  reports: { total: number; items: (Station & { id: string; category: string; state: string; details: string; manager_response: string | null; created_at: string })[] };
  conversations: { total: number; items: (Station & {id: string; created_at: string})[] };
};

const activityNames: Record<string, string> = {charging: "Charging", finished_plugged: "Finished, still connected", waiting: "Waiting", offered: "Turn offered", offer_expired: "Offer expired", connected: "Connected", idle: "No active participation"};
const activityTone = (value: string) => value === "charging" ? "teal" : ["finished_plugged", "offer_expired"].includes(value) ? "amber" : value === "offered" ? "blue" : "slate";
const periodName = (days: string) => days === "0" ? "All recorded sessions" : `Sessions started in the last ${days} days`;
function Period({value, onChange}: {value: string; onChange: (value: string) => void}) {
  return <Field label="Session period"><SelectInput value={value} onChange={event => onChange(event.target.value)}><option value="0">All time</option>{[7,30,90].map(days => <option key={days} value={days}>Last {days} days</option>)}</SelectInput></Field>;
}
function Stat({label, value}: {label: string; value: string | number}) {return <div className="ev-admin-stat"><span>{label}</span><strong>{value}</strong></div>;}
function StationLink({station}: {station: Station}) {return station.can_manage ? <Link className="ev-admin-link" to={`/app/manage/chargers/${station.charger_id}`}>{station.charger_name}<ArrowUpRight size={14}/></Link> : <span>{station.charger_name}</span>;}

export function DriversPage() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "", status = params.get("status") ?? "all", charger = params.get("charger_id") ?? "", days = params.get("days") ?? "0", attention = params.get("needs_attention") === "true";
  const offset = Math.max(0, Number(params.get("offset")) || 0);
  const [search, setSearch] = useState(query);
  const change = (key: string, value: string) => setParams(previous => {const next = new URLSearchParams(previous); next.delete("offset"); if (value) next.set(key, value); else next.delete(key); return next;}, {replace:true});
  useEffect(() => {setSearch(query);}, [query]);
  useEffect(() => {if (search === query) return; const timer = setTimeout(() => change("q", search), 300); return () => clearTimeout(timer);}, [search, query]); // Debounce typing without refetching every key.
  const filters = new URLSearchParams({q:query, status, days, needs_attention:String(attention), offset:String(offset)});
  if(charger) filters.set("charger_id", charger);
  const directory = useQuery({queryKey:["admin-drivers", filters.toString()], queryFn:({signal}) => api<Directory>(`/admin/drivers?${filters}`, {signal}), refetchInterval:() => document.visibilityState === "visible" ? 15000 : false, refetchIntervalInBackground:false});
  const data = directory.data;
  const detailParams = new URLSearchParams({days}); if(charger) detailParams.set("charger_id", charger);
  return <div className="ev-admin-page">
    <header className="ev-page-heading"><div><h1>Driver overview</h1><p>Accounts, charging activity and drivers who need your attention.</p></div><Button variant="secondary" onClick={() => void directory.refetch()} disabled={directory.isFetching}><RefreshCw size={16}/>Refresh</Button></header>
    <Card><div className="ev-admin-filters"><Field label="Search drivers"><div className="ev-admin-search"><Search size={17}/><TextInput type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Name or email"/></div></Field>
      <Field label="Driver status"><SelectInput value={status} onChange={event => change("status", event.target.value)}><option value="all">All drivers</option>{Object.entries(activityNames).map(([value,label]) => <option key={value} value={value}>{label}</option>)}<option value="no_vehicle">No saved vehicle</option><option value="has_favourites">Has saved chargers</option></SelectInput></Field>
      <Field label="Charger"><SelectInput value={charger} onChange={event => change("charger_id", event.target.value)}><option value="">All chargers</option>{data?.chargers.map(row => <option key={row.id} value={row.id}>{row.display_name}</option>)}</SelectInput></Field><Period value={days} onChange={value => change("days", value)}/>
    </div><div className="ev-admin-filter-footer"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={attention} onChange={event => change("needs_attention", event.target.checked ? "true" : "")}/>Needs attention</label><button type="button" className="ev-admin-link" onClick={() => {setSearch("");setParams({});}}>Clear filters</button></div></Card>
    {directory.isError ? <ErrorPanel title="Could not load drivers" message="Please refresh to try again."/> : null}
    {directory.isPending ? <Skeleton className="h-40"/> : data ? <>
      <div className="ev-admin-stats">{[["Matching drivers",data.summary.drivers],["Charging now",data.summary.charging],["Waiting",data.summary.waiting],["Turns offered",data.summary.offered],["Finished, connected",data.summary.finished_plugged],["Open help reports",data.summary.open_reports],["Unread messages for you",data.summary.unread_messages],["Completed sessions",data.summary.completed_sessions]].map(([label,value]) => <Stat key={label} label={String(label)} value={value}/>)}</div>
      <div className="ev-admin-section-title"><h2><Users size={20}/>Drivers <span>{data.total}</span></h2><small>Current states now · {periodName(days)}</small></div>
      {data.items.length ? <div className="ev-admin-driver-list">{data.items.map(driver => <article key={driver.id} className="ev-admin-driver-row"><div className="ev-admin-driver-name"><span className="ev-admin-avatar">{driver.display_name.split(/\s+/).slice(0,2).map(word => word[0]).join("")}</span><div><Link to={`/app/manage/drivers/${driver.id}?${detailParams}`}>{driver.display_name}</Link><p>{driver.email}</p>{driver.is_demonstration ? <Badge>Demonstration account</Badge> : null}</div></div>
        <div><small>Current activity</small><Badge tone={activityTone(driver.activity_state)}>{activityNames[driver.activity_state] ?? driver.activity_state}</Badge><p className="ev-admin-muted">{driver.vehicle_count} vehicles · {driver.favourite_count} saved chargers</p></div>
        <div><small>Session summary</small><strong>{driver.session_summary.completed} completed</strong><p className="ev-admin-muted">{formatDuration(driver.session_summary.noncharging_seconds)} reported noncharging</p></div>
        <div><small>Attention</small>{driver.open_reports || driver.unread_messages ? <p>{driver.open_reports} open reports<br/>{driver.unread_messages} unread messages</p> : <span className="ev-admin-muted">No open reports or unread messages</span>}</div>
        <Link className="ev-admin-view" to={`/app/manage/drivers/${driver.id}?${detailParams}`}>View driver<ArrowUpRight size={16}/></Link></article>)}</div> : <EmptyState title="No matching drivers" message="Try another name, status or charger."/>}
      <Pagination total={data.total} limit={data.limit} offset={offset} onPage={value => setParams(previous => {const next = new URLSearchParams(previous);next.set("offset",String(value));return next;})}/>
      <p className="ev-admin-muted">Session durations come from driver reports. Estimated battery targets do not confirm a full battery or a free charger.</p>
    </> : null}
  </div>;
}

export function AdminDriverPage() {
  const {driverId=""} = useParams(); const [params,setParams] = useSearchParams();
  const days = params.get("days") ?? "0", charger = params.get("charger_id") ?? "", offset = Math.max(0, Number(params.get("offset")) || 0);
  const filters = new URLSearchParams({days, offset:String(offset)}); if(charger) filters.set("charger_id",charger);
  const detail = useQuery({queryKey:["admin-driver",driverId,filters.toString()],queryFn:({signal}) => api<DriverDetail>(`/admin/drivers/${driverId}?${filters}`,{signal}),refetchInterval:() => document.visibilityState === "visible" ? 15000 : false,refetchIntervalInBackground:false});
  if(detail.isPending) return <Skeleton className="h-60"/>;
  if(detail.isError || !detail.data) return <ErrorPanel title="Could not load this driver" message="Refresh the page or return to the driver overview."/>;
  const data = detail.data;
  return <div className="ev-admin-page"><Link className="ev-admin-link" to={`/app/manage/drivers?${new URLSearchParams(charger ? {charger_id:charger,days} : {days})}`}><ArrowLeft size={16}/>All drivers</Link>
    <header className="ev-page-heading"><div><h1>{data.driver.display_name}</h1><p>{data.driver.email}</p><small className="ev-admin-muted">Registered {formatWhen(data.driver.created_at)}{data.driver.is_demonstration ? " · Demonstration account" : ""}</small></div><Button variant="secondary" disabled={detail.isFetching} onClick={() => void detail.refetch()}><RefreshCw size={16}/>Refresh</Button></header>
    {data.queue ? <Card><div className="ev-admin-section-title"><h2>Current waiting list</h2><Badge tone="blue">{data.queue.state === "offered" && data.queue.offer_expires_at && Date.parse(data.queue.offer_expires_at) <= Date.now() ? "Offer expired" : activityNames[data.queue.state]}</Badge></div><StationLink station={data.queue}/><p className="ev-admin-muted">Joined {formatWhen(data.queue.joined_at)}{data.queue.offer_expires_at ? ` · Offer expires ${formatWhen(data.queue.offer_expires_at)}` : ""}</p></Card> : null}
    <div className="ev-admin-section-title"><div><h2><Clock3 size={20}/>Session summary</h2><small>{periodName(days)}{charger ? " · Selected charger" : ""}</small></div><Period value={days} onChange={value => setParams(previous => {const next=new URLSearchParams(previous);next.set("days",value);next.delete("offset");return next;})}/></div>
    <div className="ev-admin-stats ev-admin-stats-four"><Stat label="Recorded sessions" value={data.session_summary?.sessions ?? 0}/><Stat label="Completed sessions" value={data.session_summary?.completed ?? 0}/><Stat label="Reported charging" value={formatDuration(data.session_summary?.charging_seconds ?? 0)}/><Stat label="Reported noncharging" value={formatDuration(data.session_summary?.noncharging_seconds ?? 0)}/></div>
    {data.sessions.items.length ? data.sessions.items.map(session => <Card key={session.id}><div className="ev-admin-section-title"><StationLink station={session}/><Badge tone={session.state === "charging" ? "teal" : session.state === "finished_plugged" ? "amber" : "slate"}>{stateLabel(session.state)}</Badge></div><p className="ev-admin-muted">{formatWhen(session.plugged_in_at)} → {session.unplugged_at ? formatWhen(session.unplugged_at) : "Still connected"}{session.port_type ? ` · ${session.port_type}` : ""}{session.is_demonstration ? " · Demonstration activity" : ""}</p>
      <dl className="ev-admin-session-values"><div><dt>Connected</dt><dd>{formatDuration(session.connected_seconds)}</dd></div><div><dt>Reported charging</dt><dd>{formatDuration(session.charging_seconds)}</dd></div><div><dt>Reported noncharging</dt><dd>{formatDuration(session.noncharging_seconds)}</dd></div></dl>
      {session.estimate ? <div className="ev-admin-estimate"><strong>{session.estimate.vehicle_label}</strong><span>Last entered: {session.estimate.current_percent}% · Target: {session.estimate.target_percent}%</span><span>Estimated target time: {formatWhen(session.estimate.estimated_target_at)}</span></div> : <p className="ev-admin-muted">No charging estimate saved.</p>}
      <p className="ev-admin-muted">Return reminder: {session.reminder?.delivered_at ? `Sent ${formatWhen(session.reminder.delivered_at)}` : session.reminder?.enabled ? `Enabled · ${formatWhen(session.reminder.due_at)}` : "Off"}</p>
    </Card>) : <EmptyState title="No sessions in this period" message="Choose another period to view earlier charging activity."/>}
    <Pagination total={data.sessions.total} offset={offset} limit={data.sessions.limit} onPage={value => setParams(previous => {const next=new URLSearchParams(previous);next.set("offset",String(value));return next;})}/>
    <div className="ev-admin-detail-grid"><Card><h2 className="ev-admin-card-title"><Car size={19}/>Saved vehicles <span>{data.vehicles.length}</span></h2>{data.vehicles.length ? data.vehicles.map(vehicle => <div key={vehicle.id} className="ev-admin-mini-row"><strong>{vehicle.nickname}</strong><p>{vehicle.model_name ?? "Model not entered"}</p><small>{vehicle.battery_capacity_kwh ? `${vehicle.battery_capacity_kwh} kWh` : "Capacity not entered"} · AC {vehicle.max_ac_kw ?? "—"} kW · DC {vehicle.max_dc_kw ?? "—"} kW</small></div>) : <p className="ev-admin-muted">No saved vehicles.</p>}</Card>
      <Card><h2 className="ev-admin-card-title"><Heart size={19}/>Saved chargers <span>{data.favourites.total}</span></h2>{data.favourites.items.length ? data.favourites.items.map(row => <div className="ev-admin-mini-row" key={row.charger_id}><StationLink station={row}/></div>) : <p className="ev-admin-muted">No saved chargers.</p>}{data.favourites.total > data.favourites.items.length ? <p className="ev-admin-muted">Showing the latest 20.</p> : null}</Card>
      <Card><h2 className="ev-admin-card-title"><MessageSquare size={19}/>Manager conversations <span>{data.conversations.total}</span></h2>{data.conversations.items.length ? data.conversations.items.map(row => <div className="ev-admin-mini-row" key={row.id}><StationLink station={row}/><p>{row.can_manage ? <Link className="ev-admin-link" to={`/app/messages/${row.id}`}>Open messages<ArrowUpRight size={14}/></Link> : "Assigned manager handles this conversation"}</p></div>) : <p className="ev-admin-muted">No manager conversations.</p>}{data.conversations.total > data.conversations.items.length ? <p className="ev-admin-muted">Showing the latest 20.</p> : null}</Card>
      <Card><h2 className="ev-admin-card-title">Help reports <span>{data.reports.total}</span></h2>{data.reports.items.length ? data.reports.items.map(row => <div className="ev-admin-mini-row" key={row.id}><div className="ev-admin-section-title"><strong>{row.category === "access_blocked" ? "Access blocked" : "Charger not working"}</strong><Badge tone={row.state === "resolved" ? "teal" : "amber"}>{row.state}</Badge></div><StationLink station={row}/><p>{row.details || "No extra details."}</p>{row.manager_response ? <p>Manager: {row.manager_response}</p> : null}<small>{formatWhen(row.created_at)}</small></div>) : <p className="ev-admin-muted">No help reports.</p>}{data.reports.total > data.reports.items.length ? <p className="ev-admin-muted">Showing the latest 20.</p> : null}</Card>
    </div>
  </div>;
}
