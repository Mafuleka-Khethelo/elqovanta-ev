import { ArrowDownLeft, ArrowRight, ArrowUpRight, Bell, CheckCircle2, Heart, History, MapPin, MessageSquare, PlugZap, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { ChargerCard, QueueView, Session } from "../../lib/types";
import { formatDuration, formatWhen, stateLabel, statusLabel } from "../../lib/format";
import { Badge, ErrorPanel, Skeleton, statusTone } from "../../components/ui";
import { useAuth } from "../../app/providers";
import { NextActions } from "../coordination/NextActions";
import { useOffline } from "../coordination/Updates";
import { ChargerGuidance } from "../chargers/ChargerGuidance";
import { VehicleChoice } from "../vehicles/VehicleChoice";

export function DriverDashboard() {
  const { user } = useAuth();
  const offline = useOffline();
  const queue = useQuery({ queryKey: ["queue"], queryFn: () => api<QueueView>("/queue"), refetchInterval: () => document.visibilityState === "visible" ? 5000 : false, refetchIntervalInBackground: false });
  const session = useQuery({ queryKey: ["session"], queryFn: () => api<{ session: Session | null }>("/sessions/current"), refetchInterval: () => document.visibilityState === "visible" ? 5000 : false, refetchIntervalInBackground: false });
  const favourites = useQuery({ queryKey: ["favourites"], queryFn: () => api<{ items: ChargerCard[] }>("/favourites") });
  const history = useQuery({ queryKey: ["history", 0], queryFn: () => api<{ items: Session[]; total: number }>("/sessions/history?limit=5&offset=0") });
  const notices = useQuery({ queryKey: ["unread"], queryFn: () => api<{ unread: number }>("/notifications/unread-count") });
  const threads = useQuery({ queryKey: ["conversations"], queryFn: () => api<{ items: { unread: number }[] }>("/conversations") });
  const current = session.data?.session;
  const waiting = queue.data?.participation === "waiting";
  const offered = queue.data?.participation === "offered";
  const participating = !!current || waiting || offered || queue.data?.participation === "session";
  const messageUnread = threads.data?.items.reduce((sum, item) => sum + item.unread, 0);
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const firstName = user?.display_name.trim().split(/\s+/)[0] ?? "there";
  const fetching = queue.isFetching || session.isFetching || favourites.isFetching || history.isFetching;
  const updatedAt = Math.min(queue.dataUpdatedAt, session.dataUpdatedAt);
  const coreError = queue.isError || session.isError || queue.isPaused || session.isPaused || offline;
  const loading = queue.isLoading || session.isLoading;
  const stationName = current?.charger_name ?? queue.data?.charger?.display_name;
  const summary = [
    { label: "Completed stops", value: history.data?.total, icon: History, to: "/app/history", detail: "Your charging history", failed: history.isError },
    { label: "Saved chargers", value: favourites.data?.items.length, icon: Heart, to: "/app/favourites", detail: "Your favourite locations", failed: favourites.isError },
    { label: "Notifications", value: notices.data?.unread, icon: Bell, to: "/app/notifications", detail: "Unread updates", failed: notices.isError },
    { label: "Messages", value: messageUnread, icon: MessageSquare, to: "/app/messages", detail: "Unread station messages", failed: threads.isError },
  ];

  async function refresh() {
    await Promise.all([queue.refetch(), session.refetch(), favourites.refetch(), history.refetch(), notices.refetch(), threads.refetch()]);
  }

  return <div className="ev-dashboard">
    <header className="ev-page-heading">
      <div><h1>Dashboard</h1><p>{greeting}, {firstName}.</p></div>
      <div className="ev-heading-actions">
        <span className="ev-updated">{updatedAt > 0 ? `Updated ${new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(updatedAt)}` : "Your charging overview"}</span>
        <button type="button" className="ev-icon-button ev-refresh" aria-label="Refresh dashboard" disabled={fetching} onClick={() => void refresh()}><RefreshCw size={17} className={fetching ? "ev-spin" : ""} /></button>
      </div>
    </header>
    {coreError ? <ErrorPanel title="Your latest stop could not be refreshed" message="The last known information is shown. Refresh before taking an action; action controls are disabled until updates recover." /> : null}

    <VehicleChoice findLink />
    <div className="ev-summary-grid">
      {summary.map(item => <Link className="ev-summary-card" to={item.to} key={item.label}>
        <span className="ev-summary-icon"><item.icon size={20} strokeWidth={1.7} /></span>
        <div><span>{item.label}</span><strong>{item.value ?? "—"}</strong>{item.failed ? <small>Open to retry.</small> : null}</div>
        <ArrowUpRight size={16} className="ev-summary-arrow" />
      </Link>)}
    </div>

    {loading ? <Skeleton className="h-48" /> : queue.data && session.data ? <section className="ev-current-stop" aria-labelledby="current-stop-title">
      <div className="ev-current-stop-content">
        <div className="ev-current-stop-heading">
          <span className="ev-current-stop-icon"><PlugZap size={23} strokeWidth={1.7} /></span>
          <div>
            <p className="ev-eyebrow">CHARGING STATUS</p>
            <h2 id="current-stop-title">{current ? "Your current session" : offered ? "Your offer is ready" : waiting ? "You are in the waiting list" : "Ready to charge"}</h2>
            {participating ? <p>{stationName ?? "Your active charging stop"}</p> : null}
            {current ? <span className="ev-current-state">{stateLabel(current.state)}</span> : null}
          </div>
        </div>
        <NextActions session={current} queue={queue.data} receivedAt={queue.dataUpdatedAt} stale={coreError} />
      </div>
      {participating ? <div className="ev-stop-facts">
        {current ? <>
          <div><span>Connected</span><strong>{formatDuration(current.connected_seconds)}</strong></div>
          <div><span>Charging</span><strong>{formatDuration(current.charging_seconds)}</strong></div>
          <div><span>Not charging</span><strong>{formatDuration(current.noncharging_seconds)}</strong></div>
        </> : waiting ? <>
          <div><span>Your position</span><strong>{queue.data?.position ?? "—"}</strong></div>
          <div><span>Drivers in line</span><strong>{queue.data?.waiting_count ?? "—"}</strong></div>
          <div><span>Station update</span><strong className="ev-fact-label">{queue.data?.charger ? statusLabel(queue.data.charger.app_status) : "Not reported"}</strong></div>
        </> : offered ? <div><span>Accept your offer before</span><strong className="ev-fact-label">{formatWhen(queue.data?.offer_expires_at)}</strong></div> : <div><span>Your stop</span><strong className="ev-fact-label">An open session is linked to your account.</strong></div>}
        {current?.is_demonstration ? <span className="ev-demo-chip">Demonstration activity</span> : null}
      </div> : null}
      {current ? <div className="px-5 pb-4 pt-3"><ChargerGuidance chargerId={current.charger_id} sessionId={current.id} /></div> : null}
    </section> : null}

    {!participating ? <Link className="ev-plan-arrival-link" to="/app/chargers"><span className="ev-summary-icon"><PlugZap size={20} /></span><div><strong>Plan your arrival</strong><span>Choose a charger, port and time to see your automatic charging advisory.</span></div><ArrowRight size={20} /></Link> : null}

    <div className="ev-driver-columns">
      <section className="ev-panel">
        <header className="ev-panel-heading"><h2>Recent charging sessions</h2><Link to="/app/history">View all<ArrowUpRight size={15} /></Link></header>
        {history.isLoading ? <div className="ev-panel-pad"><Skeleton /></div> : history.isError ? <div className="ev-panel-pad"><ErrorPanel message="Your recent sessions could not be loaded. Refresh to try again." /></div> : history.data?.items.length ? <div className="ev-history-list">
          {history.data.items.map(item => <div className="ev-history-row" key={item.id}>
            <span className="ev-row-icon"><ArrowDownLeft size={20} /></span>
            <div className="ev-history-main"><strong>{item.charger_name}</strong><small>{formatWhen(item.unplugged_at)}</small><span>Charging {formatDuration(item.charging_seconds)} · Not charging {formatDuration(item.noncharging_seconds)}</span>{item.is_demonstration ? <span className="ev-demo-chip">Demonstration activity</span> : null}</div>
            <div className="ev-history-end"><strong>{formatDuration(item.connected_seconds)}</strong><span><CheckCircle2 size={11} />{stateLabel(item.state)}</span></div>
          </div>)}
        </div> : <div className="ev-empty"><span><History size={23} strokeWidth={1.5} /></span><h3>No completed sessions yet</h3><Link to="/app/chargers">Find a charger<ArrowRight size={15} /></Link></div>}
      </section>
      <section className="ev-panel ev-saved-panel">
        <header className="ev-panel-heading"><h2>Saved chargers</h2><Heart size={19} /></header>
        {favourites.isLoading ? <div className="ev-panel-pad"><Skeleton /></div> : favourites.isError ? <div className="ev-panel-pad"><ErrorPanel message="Your saved chargers could not be loaded. Refresh to try again." /></div> : favourites.data?.items.length ? <div className="ev-saved-list">
          {favourites.data.items.slice(0, 4).map(charger => <Link className="ev-saved-charger" to={`/app/chargers/${charger.id}`} key={charger.id}>
            <span className="ev-row-icon"><MapPin size={19} /></span>
            <div><strong>{charger.display_name}</strong><span>{charger.port_types.map(port => port.name).slice(0, 2).join(" · ") || "See station details"}</span><Badge tone={statusTone(charger.app_status)}>{statusLabel(charger.app_status)}</Badge></div><ArrowUpRight size={16} />
          </Link>)}
          <Link className="ev-saved-all" to="/app/favourites">All saved chargers<ArrowRight size={15} /></Link>
        </div> : <div className="ev-empty"><span><Heart size={23} strokeWidth={1.5} /></span><h3>No saved chargers yet</h3><Link to="/app/chargers">Browse chargers<ArrowRight size={15} /></Link></div>}
      </section>
    </div>
  </div>;
}
