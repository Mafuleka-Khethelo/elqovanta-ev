import { useState, type FormEvent } from "react";
import { Activity, ArrowUpRight, CheckCheck, ChevronLeft, ChevronRight, Clock3, MapPin, MessageSquare, Plus, PlugZap, RefreshCw, Search, Users, X } from "lucide-react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../../lib/api";
import { eventLabel, formatWhen, statusLabel } from "../../lib/format";
import { Badge, Button, ErrorPanel, Field, Skeleton, TextInput, statusTone } from "../../components/ui";

type Overview = {
  chargers: { id: string; display_name: string; station_key: string; app_status: string; status_updated_at: string | null; active_sessions: number; waiting: number; offered: number; coordination_enabled: boolean; service_capacity: number | null }[];
  active_sessions: number;
  waiting_participants: number;
  completed_sessions: number;
  reported_noncharging_minutes: number;
  activity: { event_type: string; reason: string | null; created_at: string; charger_name: string; actor_name: string | null; is_demonstration: boolean }[];
};

export function ManagerHomePage() {
  const overview = useQuery({ queryKey: ["manager-overview"], queryFn: () => api<Overview>("/manager/overview"), refetchInterval: () => document.visibilityState === "visible" ? 10000 : false, refetchIntervalInBackground: false });
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState("1");
  const [timezone, setTimezone] = useState("UTC");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(0);
  const [allActivity, setAllActivity] = useState(false);
  const data = overview.data;
  const chargers = data?.chargers.filter(charger => (status === "all" || charger.app_status === status) && `${charger.display_name} ${charger.station_key}`.toLowerCase().includes(search.toLowerCase().trim())) ?? [];
  const pageSize = 6;
  const pageCount = Math.max(1, Math.ceil(chargers.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const visibleChargers = chargers.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  const number = (value: number | undefined) => value === undefined ? "—" : new Intl.NumberFormat(undefined, {maximumFractionDigits: 1}).format(value);

  async function createCharger(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    setError(null);
    setPending(true);
    try {
      await api("/manager/chargers", { method: "POST", body: { display_name: name, service_capacity: Number(capacity), app_status: "available", port_types: [], timezone } });
      setName(""); setCapacity("1"); setTimezone("UTC"); setAdding(false);
      await overview.refetch();
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Could not add the charger."); }
    finally { setPending(false); }
  }

  return <div className="ev-dashboard ev-manager-dashboard">
    <header className="ev-page-heading"><div><h1>Station dashboard</h1><p>Manage your assigned chargers, sessions and waiting lists.</p></div><div className="ev-heading-actions"><button className="ev-icon-button ev-refresh" type="button" aria-label="Refresh overview" disabled={overview.isFetching} onClick={() => void overview.refetch()}><RefreshCw size={17} className={overview.isFetching ? "ev-spin" : ""} /></button><button className="ev-button" type="button" aria-expanded={adding} aria-controls="add-charger-form" onClick={() => setAdding(!adding)}>{adding ? <X size={17} /> : <Plus size={17} />}{adding ? "Close form" : "Add charger"}</button></div></header>
    {overview.isError ? <ErrorPanel title="Could not refresh your overview" message="Please try refreshing again. Previously loaded information is shown when available." /> : null}
    {error ? <ErrorPanel message={error} /> : null}
    {adding ? <section className="ev-panel ev-add-charger" id="add-charger-form"><header className="ev-panel-heading"><div><p className="ev-eyebrow">GROW YOUR CHARGING SPACE</p><h2>Add a charger</h2></div><PlugZap size={24} /></header><form onSubmit={event => void createCharger(event)} className="ev-add-form" aria-busy={pending}><Field label="Charger name"><TextInput value={name} onChange={event => setName(event.target.value)} required minLength={2} placeholder="Give your charger a name" /></Field><Field label="Places drivers can use"><TextInput type="number" min={1} max={20} step={1} required value={capacity} onChange={event => setCapacity(event.target.value)} /></Field><Field label="Charger timezone"><select className="min-h-[43px] w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" value={timezone} onChange={event=>setTimezone(event.target.value)}><option value="UTC">UTC</option><option value="America/Los_Angeles">Palo Alto / Los Angeles</option><option value="Africa/Johannesburg">Johannesburg</option><option value="Europe/London">London</option></select></Field><Button type="submit" disabled={pending}>{pending ? "Adding…" : "Add charger"}<ArrowUpRight size={16} /></Button></form></section> : null}
    <div className="ev-manager-stats">{[
      { label:"Open sessions", value:data?.active_sessions, icon:PlugZap, detail:"Current driver-reported sessions", accent:true },
      { label:"Drivers waiting", value:data?.waiting_participants, icon:Users, detail:"Across your assigned chargers" },
      { label:"Completed stops", value:data?.completed_sessions, icon:CheckCheck, detail:"Recorded completed sessions" },
      { label:"Minutes not charging", value:data?.reported_noncharging_minutes, icon:Clock3, detail:"Reported time still connected" },
    ].map(item => <section className={`ev-manager-stat${item.accent ? " is-featured" : ""}`} key={item.label}><div><span>{item.label}</span><item.icon size={19} strokeWidth={1.6} /></div><strong>{number(item.value)}</strong><small>{item.detail}</small></section>)}</div>
    <div className="ev-manager-columns"><section className="ev-panel ev-station-panel"><header className="ev-panel-heading"><div><p className="ev-eyebrow">YOUR CHARGING NETWORK</p><h2>Your chargers <span className="ev-total-badge">{data?.chargers.length ?? "—"}</span></h2></div><MapPin size={21} /></header><div className="ev-station-filters"><label className="ev-station-search"><Search size={17} /><span className="sr-only">Search your chargers</span><input type="search" value={search} onChange={event => { setSearch(event.target.value); setPage(0); }} placeholder="Search your chargers" /></label><label><span className="sr-only">Filter by station status</span><select aria-label="Filter by station status" value={status} onChange={event => { setStatus(event.target.value); setPage(0); }}><option value="all">All statuses</option>{["available","occupied","paused","offline","unknown"].map(value => <option value={value} key={value}>{statusLabel(value)}</option>)}</select></label></div>
      {overview.isLoading ? <div className="ev-panel-pad"><Skeleton className="h-52" /></div> : !data ? <div className="ev-empty"><span><PlugZap size={25} /></span><h3>Let’s reconnect.</h3><p>Refresh your overview to load your assigned chargers.</p><button type="button" onClick={() => void overview.refetch()}>Try again<RefreshCw size={14} /></button></div> : chargers.length ? <div className="ev-station-list"><div className="ev-station-list-labels" aria-hidden="true"><span>CHARGING STATION</span><span>STATUS</span><span>OPEN</span><span>WAITING</span><span /></div>{visibleChargers.map(charger => <article className="ev-station-row" key={charger.id}><div className="ev-station-identity"><span className="ev-row-icon"><PlugZap size={20} /></span><div><Link to={`/app/manage/chargers/${charger.id}`}>{charger.display_name}</Link><small>Updated {formatWhen(charger.status_updated_at)}</small>{!charger.coordination_enabled ? <small>Coordination not enabled</small> : null}</div></div><div className="ev-station-status"><Badge tone={statusTone(charger.app_status)}>{statusLabel(charger.app_status)}</Badge></div><div className="ev-station-number"><strong>{charger.active_sessions}</strong><span>Open sessions</span></div><div className="ev-station-number"><strong>{charger.waiting}</strong><span>Waiting</span>{charger.offered > 0 ? <small>{charger.offered} offered</small> : null}</div><Link className="ev-icon-button" to={`/app/manage/chargers/${charger.id}`} aria-label={`Open ${charger.display_name}`}><ArrowUpRight size={18} /></Link></article>)}</div> : <div className="ev-empty"><span><Search size={24} /></span><h3>{data.chargers.length ? "No matching chargers." : "A new beginning."}</h3><p>{data.chargers.length ? "Try a different name or station status." : "Your assigned chargers will appear here. You can also add a charger to get started."}</p>{data.chargers.length ? <button type="button" onClick={() => {setSearch("");setStatus("all");setPage(0);}}>Clear filters<ArrowUpRight size={15} /></button> : <button type="button" onClick={() => setAdding(true)}>Add your first charger<Plus size={15} /></button>}</div>}
      <div className="ev-panel-bottom"><span>{data ? chargers.length ? `${currentPage * pageSize + 1}–${Math.min((currentPage + 1) * pageSize, chargers.length)} of ${chargers.length} chargers` : "No matching chargers" : "Your assigned chargers"}</span><div className="ev-pagination" aria-label="Charger pages"><button type="button" aria-label="Previous charger page" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={15} /></button><span>{currentPage + 1} / {pageCount}</span><button type="button" aria-label="Next charger page" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}><ChevronRight size={15} /></button></div></div>
    </section><section className="ev-panel ev-activity-panel"><header className="ev-panel-heading"><div><p className="ev-eyebrow">THE LATEST AT YOUR STATIONS</p><h2>Activity feed</h2></div><Activity size={20} /></header>{overview.isLoading ? <div className="ev-panel-pad"><Skeleton className="h-52" /></div> : data?.activity.length ? <div className="ev-activity-list">{data.activity.slice(0, allActivity ? undefined : 6).map((item,index) => <div className="ev-activity-row" key={`${item.created_at}-${index}`}><span className="ev-activity-icon"><Activity size={15} /></span><div><strong>{eventLabel(item.event_type)}</strong><p>{item.actor_name ?? "System"} · {item.charger_name}</p>{item.reason ? <p>{item.reason}</p> : null}<small>{formatWhen(item.created_at)}</small>{item.is_demonstration ? <span className="ev-demo-chip">Demonstration activity</span> : null}</div></div>)}{data.activity.length > 6 ? <button className="ev-activity-more" type="button" aria-expanded={allActivity} onClick={() => setAllActivity(!allActivity)}>{allActivity ? "Show less" : "Show all activity"}<ArrowUpRight size={14} /></button> : null}</div> : <div className="ev-empty"><span><Activity size={25} strokeWidth={1.5} /></span><h3>{data ? "A quiet moment." : "Activity unavailable."}</h3><p>{data ? "Driver reports and session updates will appear here as they happen." : "Refresh to load your station activity."}</p></div>}<Link className="ev-activity-message" to="/app/messages"><MessageSquare size={17} />Keep the conversation moving<ArrowUpRight size={15} /></Link></section></div>
    <div className="ev-dashboard-footnote"><Clock3 size={14} /><span>Your station overview refreshes automatically while this page is open.</span></div>
  </div>;
}
