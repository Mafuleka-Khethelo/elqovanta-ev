import { useId, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Car, ChevronDown, Plus, Star } from "lucide-react";
import { api, ApiError } from "../../lib/api";
import type { Vehicle } from "../../lib/types";
import { Badge, Button, Card, ErrorPanel, Field, PageHeader, SelectInput, TextInput } from "../../components/ui";
import { models, variants } from "./catalogue";
import { useVehicleSelection } from "./VehicleChoice";
import { useOffline } from "../coordination/Updates";

const blank = { nickname: "", model: "", version: "", capacity: "", ac: "", dc: "", port: "" };
export function VehiclesPage() {
  const { vehicles, selection, selected, failed } = useVehicleSelection();
  const client = useQueryClient(), offline = useOffline();
  const [draft, setDraft] = useState(blank), [editing, setEditing] = useState<string | null>(null);
  const [open, setOpen] = useState(false), [active, setActive] = useState(0);
  const [pending, setPending] = useState(false), [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const form = useRef<HTMLFormElement>(null), listId = useId();
  const matches = models.filter(m => m.toLowerCase().includes(draft.model.toLowerCase()));
  const specs = variants.filter(v => v.model === draft.model);
  const source = specs.find(v => v.version === draft.version)?.source;
  const blocked = pending || offline;
  async function refresh() { await Promise.all([client.invalidateQueries({ queryKey: ["vehicles"] }), client.invalidateQueries({ queryKey: ["vehicle-selection"] })]); }
  async function run(action: () => Promise<void>) { setPending(true); setError(""); setMessage(""); try { await action(); await refresh(); } catch(e) { setError(e instanceof ApiError ? e.message : "Could not save this change."); } finally { setPending(false); } }
  function chooseModel(model: string) { setDraft(d => ({ ...d, model, version: "", capacity: "", ac: "", dc: "" })); setOpen(false); }
  function chooseVersion(version: string) { const v = specs.find(v => v.version === version); setDraft(d => ({ ...d, version, capacity: v ? String(v.capacity) : "", ac: v?.ac ? String(v.ac) : "", dc: v?.dc ? String(v.dc) : "" })); }
  async function save(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const saved = await api<Vehicle>(editing ? `/me/vehicles/${editing}` : "/me/vehicles", { method: editing ? "PATCH" : "POST", body: {
        nickname: draft.nickname, model_name: [draft.model, draft.version].filter(Boolean).join(" · "), port_preference: draft.port || null,
        battery_capacity_kwh: Number(draft.capacity), max_ac_kw: draft.ac ? Number(draft.ac) : null, max_dc_kw: draft.dc ? Number(draft.dc) : null,
      }});
      if (!editing) await api("/me/vehicle-selection", { method: "PUT", body: { vehicle_id: saved.id, make_default: !vehicles.data?.length } });
      setEditing(null); setDraft(blank); setOpen(false); setMessage("Vehicle saved. You can now choose a charger.");
    });
  }
  function edit(v: Vehicle) {
    setEditing(v.id); setDraft({ nickname: v.nickname, model: v.model_name || "", version: "", capacity: v.battery_capacity_kwh ? String(v.battery_capacity_kwh) : "", ac: v.max_ac_kw ? String(v.max_ac_kw) : "", dc: v.max_dc_kw ? String(v.max_dc_kw) : "", port: v.port_preference || "" });
    form.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  return <div className="space-y-4"><PageHeader title="My vehicles" lede="Save your cars once. Choose the one you are driving before finding a charger." />
    {error || failed ? <ErrorPanel message={error || "Your vehicles could not be loaded. Refresh to try again."} /> : null}
    {message ? <p role="status" className="rounded-xl bg-[#edf5e7] p-3 text-sm">{message}</p> : null}
    <div className="grid gap-4 md:grid-cols-2">{vehicles.data?.map(v => <Card key={v.id}><div className="flex items-start gap-3"><Car className="mt-1 shrink-0 text-primary" /><div className="min-w-0"><h2 className="font-semibold">{v.nickname}</h2><p className="break-words text-sm text-slate-600">{v.model_name || "Model not specified"}</p><p className="mt-2 text-sm">{v.battery_capacity_kwh ? `${v.battery_capacity_kwh} kWh usable` : "Add battery capacity"}</p><div className="mt-2 flex gap-2">{v.id === selected?.id ? <Badge tone="teal">Driving today</Badge> : null}{v.id === selection.data?.default_vehicle_id ? <Badge>Default</Badge> : null}</div></div></div>
      <div className="mt-4 flex flex-wrap gap-2"><Button disabled={blocked || v.id === selected?.id} onClick={() => void run(async () => { await api("/me/vehicle-selection", { method: "PUT", body: { vehicle_id: v.id } }); })}>Use this car</Button><Button variant="secondary" disabled={blocked} onClick={() => edit(v)}>Edit</Button><Button variant="ghost" disabled={blocked || v.id === selection.data?.default_vehicle_id} onClick={() => void run(async () => { await api("/me/vehicle-selection", { method: "PUT", body: { vehicle_id: v.id, make_default: true } }); })}><Star size={15} /> Make default</Button><Button variant="ghost" disabled={blocked} onClick={() => void run(async () => { await api(`/me/vehicles/${v.id}`, { method: "DELETE" }); if (editing === v.id) { setEditing(null); setDraft(blank); } })}>Remove</Button></div>
    </Card>)}</div>
    {selected ? <Link className="inline-flex rounded-lg bg-[#24645d] px-4 py-2 text-sm font-semibold text-white" to="/app/chargers">Find chargers for {selected.nickname}</Link> : null}
    <Card><h2 className="flex items-center gap-2 text-lg font-semibold"><Plus size={20} />{editing ? "Edit vehicle" : "Add a vehicle"}</h2><p className="mt-1 text-sm text-slate-500">Up to five cars. Search the suggestions or enter a model that is missing.</p>
      <form ref={form} className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={event => void save(event)}>
        <Field label="Nickname"><TextInput required maxLength={40} disabled={blocked} placeholder="e.g. My everyday car" value={draft.nickname} onChange={e => setDraft(d => ({ ...d, nickname: e.target.value }))} /></Field>
        <div className="relative" onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false); }}>
          <Field label="Car make and model"><div className="flex gap-1"><TextInput role="combobox" aria-expanded={open} aria-controls={listId} aria-autocomplete="list" aria-activedescendant={open && matches[active] ? `${listId}-${active}` : undefined} autoComplete="off" required maxLength={60} disabled={blocked} placeholder="Search e.g. BMW, BYD, Tesla" value={draft.model} onFocus={() => { setOpen(true); setActive(0); }} onChange={e => { setDraft(d => ({ ...d, model: e.target.value, version: "", capacity: "", ac: "", dc: "" })); setOpen(true); setActive(0); }} onKeyDown={e => { if (e.key === "Escape") setOpen(false); if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); setOpen(true); setActive(i => Math.max(0, Math.min(matches.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))); } if (e.key === "Enter" && open && matches[active]) { e.preventDefault(); chooseModel(matches[active]); } }} /><button type="button" className="rounded-lg border border-slate-300 px-2" aria-label="Show vehicle models" disabled={blocked} onClick={() => setOpen(!open)}><ChevronDown size={18} /></button></div></Field>
          {open ? <ul id={listId} role="listbox" aria-label="Vehicle model suggestions" className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg">{matches.map((m, i) => <li id={`${listId}-${i}`} key={m} role="option" aria-selected={i === active} className={`cursor-pointer px-3 py-2 text-sm hover:bg-[#edf5e7] ${i === active ? "bg-[#edf5e7]" : ""}`} onMouseDown={e => { e.preventDefault(); chooseModel(m); }}>{m}</li>)}{!matches.length ? <li className="p-3 text-sm text-slate-500">No match. Your typed model will be saved.</li> : null}</ul> : null}
        </div>
        {specs.length ? <Field label="Year and version"><SelectInput value={draft.version} disabled={blocked} onChange={e => chooseVersion(e.target.value)}><option value="">Enter another version manually</option>{specs.map(v => <option key={v.version}>{v.version}</option>)}</SelectInput></Field> : <Field label="Year and version (optional)"><TextInput maxLength={35} disabled={blocked} value={draft.version} placeholder="e.g. 2022 Long Range" onChange={e => setDraft(d => ({ ...d, version: e.target.value }))} /></Field>}
        <Field label="Usable battery capacity (kWh)" hint={source ? "Prefilled for this exact version; check it matches your car." : "Enter the usable capacity from your vehicle documentation."}><TextInput required type="number" min="0.1" max="500" step="0.1" disabled={blocked} value={draft.capacity} onChange={e => setDraft(d => ({ ...d, capacity: e.target.value }))} /></Field>
        <Field label="AC charging limit (kW), if known"><TextInput type="number" min="0.1" max="1000" step="0.1" disabled={blocked} value={draft.ac} onChange={e => setDraft(d => ({ ...d, ac: e.target.value }))} /></Field>
        <Field label="DC charging limit (kW), if known"><TextInput type="number" min="0.1" max="1000" step="0.1" disabled={blocked} value={draft.dc} onChange={e => setDraft(d => ({ ...d, dc: e.target.value }))} /></Field>
        {source ? <p className="text-xs text-slate-500 sm:col-span-2">Exact-version starting values from the <a className="underline" href={source} target="_blank" rel="noreferrer">manufacturer specification</a>. Other years and markets can differ. Values remain editable.</p> : null}
        <div className="flex flex-wrap gap-2 sm:col-span-2"><Button type="submit" disabled={blocked || (!editing && (vehicles.data?.length ?? 0) >= 5)}>{pending ? "Saving…" : editing ? "Save vehicle" : "Add vehicle"}</Button>{editing ? <Button type="button" variant="secondary" disabled={blocked} onClick={() => { setEditing(null); setDraft(blank); }}>Cancel editing</Button> : null}</div>
      </form>
    </Card>
  </div>;
}
