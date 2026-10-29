import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Car, ArrowRight } from "lucide-react";
import { api, ApiError } from "../../lib/api";
import type { Vehicle } from "../../lib/types";
import { Card, ErrorPanel, Field, SelectInput, Skeleton } from "../../components/ui";
import { useOffline } from "../coordination/Updates";

type Selection = { selected_vehicle_id: string | null; default_vehicle_id: string | null };
export function useVehicleSelection() {
  const vehicles = useQuery({ queryKey: ["vehicles"], queryFn: () => api<Vehicle[]>("/me/vehicles") });
  const selection = useQuery({ queryKey: ["vehicle-selection"], queryFn: () => api<Selection>("/me/vehicle-selection") });
  const selected = vehicles.data?.find(v => v.id === selection.data?.selected_vehicle_id);
  return { vehicles, selection, selected, loading: vehicles.isLoading || selection.isLoading, failed: vehicles.isError || selection.isError };
}

export function VehicleChoice({ findLink = false }: { findLink?: boolean }) {
  const { vehicles, selection, selected, loading, failed } = useVehicleSelection();
  const client = useQueryClient(), offline = useOffline();
  const [pending, setPending] = useState(false), [error, setError] = useState("");
  async function choose(id: string) {
    if (!id) return;
    setPending(true); setError("");
    try {
      const result = await api<Selection>("/me/vehicle-selection", { method: "PUT", body: { vehicle_id: id } });
      client.setQueryData(["vehicle-selection"], result);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not select your vehicle."); }
    finally { setPending(false); }
  }
  if (loading) return <Skeleton className="h-28" />;
  return <Card>
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3"><h2 className="flex items-center gap-2 text-lg font-semibold"><Car size={21} /> Which car are you driving?</h2><Link className="text-sm font-semibold text-primary underline" to="/app/vehicles">My vehicles</Link></div>
    {failed || error ? <ErrorPanel message={error || "Your vehicles could not be refreshed. Try again before planning a charge."} /> : vehicles.data?.length ? <div className="grid items-end gap-3 sm:grid-cols-[1fr_auto]">
      <Field label="Today's vehicle"><SelectInput disabled={pending || offline} value={selected?.id ?? ""} onChange={e => void choose(e.target.value)}><option value="" disabled>Select a saved vehicle</option>{vehicles.data.map(v => <option key={v.id} value={v.id}>{v.nickname}{v.model_name ? ` · ${v.model_name}` : ""}{v.id === selection.data?.default_vehicle_id ? " (default)" : ""}</option>)}</SelectInput></Field>
      {findLink && selected ? <Link className="inline-flex items-center gap-2 rounded-lg bg-[#24645d] px-4 py-2 text-sm font-semibold text-white" to="/app/chargers">Find chargers <ArrowRight size={16} /></Link> : null}
    </div> : <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-600">Add your car first. Its battery details will be ready when you plan a charge.</p><Link className="rounded-lg bg-[#24645d] px-4 py-2 text-sm font-semibold text-white" to="/app/vehicles">Add your first vehicle</Link></div>}
    {selected ? <p className="mt-2 text-xs text-slate-500">{selected.battery_capacity_kwh ? `${selected.battery_capacity_kwh} kWh usable battery` : "Battery capacity still needed"} · Choose a charger next to preview your charging time.</p> : null}
  </Card>;
}
