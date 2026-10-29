import { FormEvent, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "../../lib/api";
import type { User, Vehicle } from "../../lib/types";
import { Button, Card, ErrorPanel, Field, PageHeader, TextInput } from "../../components/ui";
import { useAuth } from "../../app/providers";

export function ProfilePage() {
  const { user, refresh } = useAuth();
  const queryClient = useQueryClient();
  const vehicles = useQuery({ queryKey: ["vehicles"], queryFn: () => api<Vehicle[]>("/me/vehicles") });
  const [name, setName] = useState(user?.display_name ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [nextPassword, setNextPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nickname, setNickname] = useState("");
  const [model, setModel] = useState("");
  const [port, setPort] = useState("");
  const [capacity, setCapacity] = useState("");
  const [acLimit, setAcLimit] = useState("");
  const [dcLimit, setDcLimit] = useState("");
  const [editing, setEditing] = useState<string | null>(null);

  async function saveName(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const result = await api<{ user: User }>("/me", { method: "PATCH", body: { display_name: name } });
      queryClient.setQueryData(["me"], { user: result.user });
      setMessage("Name saved.");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not save your name.");
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api("/auth/password", { method: "POST", body: { current_password: currentPassword, new_password: nextPassword } });
      setCurrentPassword("");
      setNextPassword("");
      setMessage("Password changed. Other sign-ins for this account were signed out.");
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not change the password.");
    }
  }

  async function addVehicle(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api(editing ? `/me/vehicles/${editing}` : "/me/vehicles", { method: editing ? "PATCH" : "POST", body: { nickname, model_name: model || null, port_preference: port || null,
        battery_capacity_kwh: capacity ? Number(capacity) : null, max_ac_kw: acLimit ? Number(acLimit) : null, max_dc_kw: dcLimit ? Number(dcLimit) : null } });
      setNickname("");
      setModel("");
      setPort("");
      setCapacity(""); setAcLimit(""); setDcLimit(""); setEditing(null);
      await queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not save the vehicle.");
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Profile" />
      {error ? <ErrorPanel message={error} /> : null}
      {message ? <p className="rounded-xl bg-[#e7eef5] px-3 py-2 text-sm text-navy">{message}</p> : null}
      <Card>
        <p className="text-sm text-slate-500">{user?.email} · {user?.role === "manager" ? "Station manager" : "Driver"}</p>
        <form className="mt-4 max-w-md space-y-3" onSubmit={(event) => void saveName(event)}>
          <Field label="Display name"><TextInput value={name} onChange={(event) => setName(event.target.value)} required minLength={2} maxLength={80} /></Field>
          <Button type="submit">Save name</Button>
        </form>
      </Card>
      <Card>
        <h2 className="font-semibold">Change password</h2>
        <form className="mt-4 max-w-md space-y-3" onSubmit={(event) => void savePassword(event)}>
          <Field label="Current password"><TextInput type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></Field>
          <Field label="New password" hint="10 to 128 characters, different from the current password."><TextInput type="password" autoComplete="new-password" value={nextPassword} onChange={(event) => setNextPassword(event.target.value)} required minLength={10} /></Field>
          <Button type="submit">Change password</Button>
        </form>
      </Card>
      {user?.role === "driver" ? (
        <Card>
          <h2 className="font-semibold">Vehicles</h2>
          <p className="mt-1 text-sm text-slate-600">Save the exact model/version and usable battery capacity for charging-time calculations. Use your vehicle's documentation; these are owner-entered details.</p>
          <ul className="mt-3 space-y-2 text-sm">
            {vehicles.data?.map((vehicle) => (
              <li key={vehicle.id} className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
                <span>{vehicle.nickname}{vehicle.model_name ? ` · ${vehicle.model_name}` : ""}{vehicle.battery_capacity_kwh ? ` · ${vehicle.battery_capacity_kwh} kWh usable` : ""}{vehicle.port_preference ? ` · ${vehicle.port_preference}` : ""}</span>
                <Button variant="ghost" onClick={() => { setEditing(vehicle.id); setNickname(vehicle.nickname); setModel(vehicle.model_name || ""); setPort(vehicle.port_preference || ""); setCapacity(vehicle.battery_capacity_kwh ? String(vehicle.battery_capacity_kwh) : ""); setAcLimit(vehicle.max_ac_kw ? String(vehicle.max_ac_kw) : ""); setDcLimit(vehicle.max_dc_kw ? String(vehicle.max_dc_kw) : ""); }}>Edit</Button>
                <Button variant="ghost" onClick={() => void api(`/me/vehicles/${vehicle.id}`, { method: "DELETE" }).then(() => queryClient.invalidateQueries({ queryKey: ["vehicles"] }))}>Remove</Button>
              </li>
            ))}
          </ul>
          <form className="mt-4 grid gap-3 md:grid-cols-3" onSubmit={(event) => void addVehicle(event)}>
            <Field label="Nickname"><TextInput value={nickname} onChange={(event) => setNickname(event.target.value)} required maxLength={40} /></Field>
            <Field label="Model and version"><TextInput value={model} onChange={(event) => setModel(event.target.value)} maxLength={60} /></Field>
            <Field label="Port preference"><TextInput value={port} onChange={(event) => setPort(event.target.value)} maxLength={60} /></Field>
            <Field label="Usable battery capacity (kWh)"><TextInput type="number" min="0.1" max="500" step="0.1" value={capacity} onChange={event => setCapacity(event.target.value)} /></Field>
            <Field label="AC charging limit (kW), if known"><TextInput type="number" min="0.1" max="1000" step="0.1" value={acLimit} onChange={event => setAcLimit(event.target.value)} /></Field>
            <Field label="DC charging limit (kW), if known"><TextInput type="number" min="0.1" max="1000" step="0.1" value={dcLimit} onChange={event => setDcLimit(event.target.value)} /></Field>
            <Button type="submit">{editing ? "Save vehicle" : "Add vehicle"}</Button>
            {editing ? <Button variant="secondary" type="button" onClick={() => { setEditing(null); setNickname(""); setModel(""); setPort(""); setCapacity(""); setAcLimit(""); setDcLimit(""); }}>Cancel editing</Button> : null}
          </form>
        </Card>
      ) : null}
    </div>
  );
}
