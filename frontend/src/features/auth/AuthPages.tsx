import { useState, type FormEvent, type ReactNode } from "react";
import { ArrowLeft, ArrowUpRight, Check, Eye, EyeOff, Leaf, LoaderCircle, LockKeyhole, Mail, ShieldCheck, UserRound, Zap } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "../../lib/api";
import type { User } from "../../lib/types";
import { ErrorPanel } from "../../components/ui";
import { BrandLogo } from "../../components/BrandLogo";
import { fieldError } from "../../lib/format";
import "./auth.css";

function destination(role: User["role"], from: string | undefined) {
  if (from && from.startsWith("/app")) return from;
  return role === "manager" ? "/app/manage" : role === "researcher" ? "/app/research/predict" : "/app";
}

export function SignInPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const from = (location.state as { from?: string } | null)?.from;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      const result = await api<{ user: User }>("/auth/login", { method: "POST", body: { email, password } });
      queryClient.setQueryData(["me"], { user: result.user });
      navigate(destination(result.user.role, from));
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Sign-in failed. Please try again."); }
    finally { setPending(false); }
  }

  return <AuthFrame mode="sign-in" title={<>Welcome<br />back.</>} lede="A better charging day starts right here. Sign in to pick up where you left off.">
    <form className="ev-auth-form" onSubmit={event => void onSubmit(event)} aria-busy={pending}>
      {error ? <ErrorPanel title="Could not sign in" message={error} /> : null}
      <AuthInput id="sign-in-email" label="Email address" type="email" value={email} onChange={setEmail} autoComplete="email" placeholder="you@example.com" />
      <PasswordInput id="sign-in-password" value={password} onChange={setPassword} />
      <button className="ev-auth-submit" type="submit" disabled={pending}>{pending ? <><LoaderCircle className="ev-spin" size={19} />Signing in…</> : <>Sign in<ArrowUpRight size={20} /></>}</button>
      <p className="ev-auth-switch">New around here? <Link to="/register" state={from ? { from } : undefined}>Create an account<ArrowUpRight size={14} /></Link></p>
    </form>
    <p className="ev-auth-account-note"><ShieldCheck size={17} />One sign-in for drivers, station managers and examiners.</p>
  </AuthFrame>;
}

export function RegisterPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<{ field: string; message: string }[]>([]);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    setFields([]);
    try {
      const result = await api<{ user: User }>("/auth/register", { method: "POST", body: { email, password, display_name: name } });
      queryClient.setQueryData(["me"], { user: result.user });
      navigate(destination(result.user.role, from));
    } catch (caught) {
      if (caught instanceof ApiError) { setError(caught.message); setFields(caught.fields); }
      else setError("Registration failed. Please try again.");
    } finally { setPending(false); }
  }

  return <AuthFrame mode="register" title={<>Let’s get you<br />moving.</>} lede="Your next stop, your place in line, your charging story. All in one account.">
    <form className="ev-auth-form" onSubmit={event => void onSubmit(event)} aria-busy={pending}>
      {error ? <ErrorPanel title="Could not create your account" message={error} /> : null}
      <AuthInput id="register-name" label="Your name" type="text" value={name} onChange={setName} autoComplete="name" placeholder="What should we call you?" error={fieldError(fields, "display_name")} />
      <AuthInput id="register-email" label="Email address" type="email" value={email} onChange={setEmail} autoComplete="email" placeholder="you@example.com" error={fieldError(fields, "email")} />
      <PasswordInput id="register-password" value={password} onChange={setPassword} registration error={fieldError(fields, "password")} />
      <button className="ev-auth-submit" type="submit" disabled={pending}>{pending ? <><LoaderCircle className="ev-spin" size={19} />Creating your account…</> : <>Create driver account<ArrowUpRight size={20} /></>}</button>
      <p className="ev-auth-switch">Already part of the journey? <Link to="/sign-in" state={from ? { from } : undefined}>Sign in<ArrowUpRight size={14} /></Link></p>
    </form>
    <p className="ev-auth-account-note"><ShieldCheck size={18} /><span>Managing a station? Your operator issues your account. <Link to="/sign-in">Sign in here.</Link></span></p>
  </AuthFrame>;
}

function AuthInput({ id, label, type, value, onChange, autoComplete, placeholder, error }: { id: string; label: string; type: "text" | "email"; value: string; onChange: (value: string) => void; autoComplete: string; placeholder: string; error?: string }) {
  const Icon = type === "email" ? Mail : UserRound;
  return <div className="ev-auth-field"><label htmlFor={id}>{label}</label><div className={`ev-auth-input${error ? " has-error" : ""}`}><Icon size={18} aria-hidden="true" /><input id={id} name={type === "email" ? "email" : "name"} type={type} value={value} onChange={event => onChange(event.target.value)} autoComplete={autoComplete} autoCapitalize={type === "email" ? "none" : "words"} spellCheck={false} placeholder={placeholder} required minLength={type === "text" ? 2 : undefined} maxLength={type === "text" ? 80 : undefined} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined} /></div>{error ? <p className="ev-auth-field-error" id={`${id}-error`}>{error}</p> : null}</div>;
}

function PasswordInput({ id, value, onChange, registration = false, error }: { id: string; value: string; onChange: (value: string) => void; registration?: boolean; error?: string }) {
  const [visible, setVisible] = useState(false);
  return <div className="ev-auth-field"><label htmlFor={id}>Password</label><div className={`ev-auth-input${error ? " has-error" : ""}`}><LockKeyhole size={18} aria-hidden="true" /><input id={id} name="password" type={visible ? "text" : "password"} value={value} onChange={event => onChange(event.target.value)} autoComplete={registration ? "new-password" : "current-password"} placeholder={registration ? "Create your password" : "Enter your password"} required minLength={registration ? 10 : undefined} maxLength={registration ? 128 : undefined} aria-invalid={!!error} aria-describedby={[registration ? `${id}-hint` : "", error ? `${id}-error` : ""].filter(Boolean).join(" ") || undefined} /><button type="button" aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>{registration ? <p id={`${id}-hint`} className={`ev-password-hint${value.length >= 10 ? " is-valid" : ""}`}><Check size={13} />Use 10–128 characters.</p> : null}{error ? <p className="ev-auth-field-error" id={`${id}-error`}>{error}</p> : null}</div>;
}

function AuthFrame({ mode, title, lede, children }: { mode: "sign-in" | "register"; title: ReactNode; lede: string; children: ReactNode }) {
  const register = mode === "register";
  return <div className={`ev-auth ev-auth-${mode}`}><a className="ev-auth-skip" href="#account-form">Skip to form</a><header className="ev-auth-header"><Link to="/" aria-label="Elqovanta EV home"><BrandLogo /></Link><Link className="ev-auth-home" to="/"><ArrowLeft size={16} />Back to home</Link></header><main className="ev-auth-layout"><section className="ev-auth-story" aria-label="A better way to charge"><div className="ev-auth-story-copy"><p className="ev-auth-eyebrow"><span />GOOD ENERGY. GREAT JOURNEYS.</p><h2>{register ? <>Big journeys.<br />Better beginnings.</> : <>Less waiting.<br /><span>More living.</span></>}</h2><p>{register ? "A little more freedom. A lot less to juggle. Make your next charging stop a good one." : "Your place in line. Your next charging stop. Your time to get on with the good stuff."}</p></div><div className="ev-auth-car-art" aria-hidden="true"><div className="ev-auth-orbit" /><span className="ev-auth-car-badge"><Zap size={19} fill="currentColor" /></span><img src={register ? "/cars/yellow-city.png" : "/cars/teal-coupe.png"} alt="" width="1536" height="1024" /></div><div className="ev-auth-story-footer"><span><Leaf size={17} />A brighter way forward.</span><span>01 / 01</span></div></section><section id="account-form" className="ev-auth-content" aria-labelledby="auth-title"><div className="ev-auth-form-wrap"><p className="ev-auth-eyebrow">{register ? "WELCOME TO ELQOVANTA EV" : "YOUR JOURNEY, CONNECTED"}</p><h1 id="auth-title">{title}</h1><p className="ev-auth-lede">{lede}</p>{children}</div><footer className="ev-auth-footer">© {new Date().getFullYear()} Elqovanta EV<span>Made for more connected journeys.</span></footer></section></main></div>;
}
