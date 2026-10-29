import { BarChart3, Bell, BrainCircuit, Car, Clock, Heart, History, Info, LayoutDashboard, LogOut, MapPinned, Menu, MessageSquare, UserRound, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuth } from "./providers";
import { BrandLogo } from "../components/BrandLogo";
import { useOffline } from "../features/coordination/Updates";
import "./workspace.css";
import "./workspace-clean.css";

export function Shell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const drawer = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const manager = user?.role === "manager";
  const offline = useOffline();
  const examiner = user?.role === "researcher";
  const unread = useQuery({ queryKey: ["unread"], queryFn: () => api<{ unread: number }>("/notifications/unread-count"), refetchInterval: () => document.visibilityState === "visible" ? 20000 : false, refetchIntervalInBackground: false });
  const threads = useQuery({ queryKey: ["conversations"], enabled: !examiner, queryFn: () => api<{ items: { unread: number }[] }>("/conversations"), refetchInterval: () => document.visibilityState === "visible" ? 20000 : false, refetchIntervalInBackground: false });
  const messageUnread = threads.data?.items.reduce((sum, item) => sum + item.unread, 0) ?? 0;
  const noticeCount = unread.data?.unread ?? 0;
  const initials = (user?.display_name ?? "EV").split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join("").toUpperCase();
  const primary = manager ? [{ to: "/app/manage", label: "Overview", icon: LayoutDashboard }] : examiner ? [] : [
    { to: "/app", label: "Overview", icon: LayoutDashboard },
    { to: "/app/chargers", label: "Find chargers", icon: MapPinned },
    { to: "/app/vehicles", label: "My vehicles", icon: Car },
    { to: "/app/session", label: "My session", icon: Car },
    { to: "/app/queue", label: "Waiting list", icon: Clock },
    { to: "/app/history", label: "Charging history", icon: History },
    { to: "/app/favourites", label: "Saved chargers", icon: Heart },
  ];
  const research = examiner ? [
    { to: "/app/research/predict", label: "Prediction lab", icon: BrainCircuit },
    { to: "/app/research", label: "Historical insights", icon: BarChart3 },
    { to: "/app/about", label: "About the model", icon: Info },
  ] : [];
  const account = [
    ...(!examiner ? [{ to: "/app/messages", label: "Messages", icon: MessageSquare, count: messageUnread }] : []),
    { to: "/app/notifications", label: "Notifications", icon: Bell, count: noticeCount },
    { to: "/app/profile", label: "My profile", icon: UserRound },
  ];
  const current = [...primary, ...research, ...account].filter(item => location.pathname === item.to || (item.to !== "/app" && location.pathname.startsWith(item.to + "/"))).sort((a, b) => b.to.length - a.to.length)[0];

  useEffect(() => { setOpen(false); }, [location.pathname]);
  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    drawer.current?.querySelector<HTMLElement>("a, button")?.focus();
    const closeOnDesktop = () => { if (window.innerWidth >= 1100) setOpen(false); };
    window.addEventListener("resize", closeOnDesktop);
    return () => { document.body.style.overflow = previousOverflow; window.removeEventListener("resize", closeOnDesktop); menuButton.current?.focus(); };
  }, [open]);

  async function logout() {
    setSigningOut(true);
    setLogoutError("");
    try {
      await api("/auth/logout", { method: "POST" });
      queryClient.clear();
      queryClient.setQueryData(["me"], { user: null });
      navigate("/");
    } catch { setLogoutError("Could not sign out. Please try again."); }
    finally { setSigningOut(false); }
  }

  function navigation() {
    return <>
      <Link to="/" aria-label="Elqovanta EV home" className="ev-sidebar-brand"><BrandLogo /></Link>
      <div className="ev-workspace-label"><span />{manager ? "STATION WORKSPACE" : examiner ? "MODEL LAB" : "YOUR CHARGING SPACE"}</div>
      <nav aria-label="Application" className="ev-navigation">
        {[{ label: "WORKSPACE", items: primary }, ...(examiner ? [{ label: "MODEL LAB", items: research }] : []), { label: "YOUR ACCOUNT", items: account }].filter(group => group.items.length > 0).map(group => <div className="ev-nav-group" key={group.label}><p>{group.label}</p>{group.items.map(item => <NavLink key={item.to} to={item.to} end={item.to === "/app" || item.to === "/app/research" || item.to === "/app/manage"} className={({ isActive }) => `ev-nav-link${isActive ? " is-active" : ""}`} onClick={() => setOpen(false)}><item.icon size={18} strokeWidth={1.7} aria-hidden="true" /><span>{item.label}</span>{"count" in item && Number(item.count) > 0 ? <span className="ev-nav-count">{Number(item.count) > 99 ? "99+" : Number(item.count)}</span> : null}</NavLink>)}</div>)}
      </nav>
      {user?.is_demonstration ? <p className="ev-demo-note">Demonstration account</p> : null}
      <div className="ev-sidebar-account"><Link to="/app/profile" className="ev-account-link"><span className="ev-avatar">{initials}</span><span><strong>{user?.display_name}</strong><small>{manager ? "Station manager" : examiner ? "Researcher" : "EV driver"}</small></span></Link><button className="ev-icon-button" aria-label="Sign out" disabled={signingOut} onClick={() => void logout()}><LogOut size={18} /></button></div>
      {logoutError ? <p className="ev-logout-error" role="alert">{logoutError}</p> : null}
    </>;
  }

  return <div className="ev-workspace">
    <a className="ev-skip" href="#main">Skip to content</a>
    <aside className="ev-sidebar">{navigation()}</aside>
    <div className="ev-workspace-body">
      <header className="ev-topbar"><div className="ev-topbar-title"><span>{manager ? "Station workspace" : examiner ? "Model lab" : "My workspace"}</span><i>/</i><strong>{current?.label ?? "Your charging"}</strong></div><Link to="/" className="ev-mobile-brand" aria-label="Elqovanta EV home"><BrandLogo /></Link><div className="ev-topbar-actions"><Link className="ev-icon-button ev-notification-link" to="/app/notifications" aria-label={`Notifications${noticeCount ? `, ${noticeCount} unread` : ""}`}><Bell size={20} />{noticeCount > 0 ? <span /> : null}</Link><span className="ev-topbar-divider" /><Link to="/app/profile" className="ev-topbar-user"><span className="ev-avatar">{initials}</span><span><strong>{user?.display_name}</strong><small>{manager ? "Station manager" : examiner ? "Researcher" : "EV driver"}</small></span></Link><button ref={menuButton} type="button" className="ev-icon-button ev-menu-button" aria-label="Open menu" aria-expanded={open} aria-controls="ev-mobile-navigation" onClick={() => setOpen(true)}><Menu size={22} /></button></div></header>
      {offline ? <p role="alert" className="mx-5 mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">You are offline. Previously loaded information is shown. Reconnect before submitting an update.</p> : null}
      <main id="main" tabIndex={-1} className="ev-main"><Outlet /></main>
      <footer className="ev-workspace-footer"><span>© {new Date().getFullYear()} Elqovanta EV</span><span>Your charging workspace</span></footer>
    </div>
    {open ? <div className="ev-drawer-layer"><button type="button" className="ev-drawer-backdrop" aria-label="Close navigation" onClick={() => setOpen(false)} /><aside ref={drawer} id="ev-mobile-navigation" className="ev-mobile-drawer" role="dialog" aria-modal="true" aria-label="Navigation" onKeyDown={event => {
      if (event.key === "Escape") setOpen(false);
      if (event.key === "Tab") {
        const nodes = drawer.current?.querySelectorAll<HTMLElement>('a, button:not(:disabled)');
        if (!nodes?.length) return;
        const first = nodes[0], last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    }}><button className="ev-icon-button ev-drawer-close" type="button" aria-label="Close menu" onClick={() => setOpen(false)}><X size={20} /></button>{navigation()}</aside></div> : null}
  </div>;
}
