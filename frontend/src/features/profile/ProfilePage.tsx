import { FormEvent, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "../../lib/api";
import type { User } from "../../lib/types";
import { Button, Card, ErrorPanel, Field, PageHeader, TextInput } from "../../components/ui";
import { Link } from "react-router-dom";
import { useAuth } from "../../app/providers";

export function ProfilePage() {
  const { user, refresh } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState(user?.display_name ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [nextPassword, setNextPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
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
      {user?.role === "driver" ? <Card><h2 className="font-semibold">Your vehicles</h2><p className="mt-2 text-sm text-slate-500">Manage your cars and choose the one you are driving.</p><Link className="mt-3 inline-block font-semibold text-primary underline" to="/app/vehicles">Open My vehicles</Link></Card> : null}
    </div>
  );
}
