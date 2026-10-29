import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { MapContainer, Marker, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import { api } from "../../lib/api";
import type { ChargerCard } from "../../lib/types";
import { statusLabel } from "../../lib/format";
import { stationTime } from "../coordination/Updates";
import { VehicleChoice, useVehicleSelection } from "../vehicles/VehicleChoice";
import { Badge, Button, Card, EmptyState, ErrorPanel, Field, PageHeader, Pagination, SelectInput, Skeleton, TextInput, statusTone } from "../../components/ui";

type ListResponse = {
  items: ChargerCard[];
  total: number;
  limit: number;
  offset: number;
  distance_label: string | null;
};

export function FindChargersPage() {
  const vehicle = useVehicleSelection();
  const [params, setParams] = useSearchParams();
  const [draft, setDraft] = useState(params.get("q") ?? "");
  const [locationError, setLocationError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(params.get("selected"));
  const view = params.get("view") === "map" ? "map" : "list";
  const offset = Number(params.get("offset") ?? "0") || 0;
  const limit = 12;

  const query = useQuery({
    queryKey: ["chargers", params.toString()],
    queryFn: () => api<ListResponse>(`/chargers?${searchQuery(params, limit, offset)}`),
  });
  const ports = useQuery({ queryKey: ["ports"], queryFn: () => api<{ items: string[] }>("/port-types") });
  const items = query.data?.items ?? [];
  const selectedCard = items.find((item) => item.id === selected) ?? items[0] ?? null;

  function update(next: Record<string, string | null>) {
    const copy = new URLSearchParams(params);
    Object.entries(next).forEach(([key, value]) => {
      if (!value) copy.delete(key);
      else copy.set(key, value);
    });
    if (!("offset" in next)) copy.delete("offset");
    setParams(copy);
  }

  function onSearch(event: FormEvent) {
    event.preventDefault();
    update({ q: draft.trim() || null });
  }

  function useLocation() {
    setLocationError(null);
    if (!navigator.geolocation) {
      setLocationError("This browser cannot share a location. The list still works.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => update({ lat: String(position.coords.latitude), lon: String(position.coords.longitude) }),
      () => setLocationError("Location permission was denied or is unavailable. The charger list still works without it."),
    );
  }

  if (!vehicle.selected || vehicle.failed) return <div className="space-y-4"><PageHeader title="Find chargers" lede="Choose your vehicle first." /><VehicleChoice /></div>;

  return (
    <div>
      <PageHeader
        title="Find chargers"
        lede="Search by name, connector, or status."
      />
      <div className="mb-4"><VehicleChoice /></div>
      <form className="mb-4 grid gap-3 md:grid-cols-4" onSubmit={onSearch}>
        <Field label="Name">
          <TextInput value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Exact or partial name" />
        </Field>
        <Field label="Connector">
          <SelectInput value={params.get("port") ?? ""} onChange={(event) => update({ port: event.target.value || null })}>
            <option value="">Any</option>
            {ports.data?.items.map((name) => <option key={name} value={name}>{name}</option>)}
          </SelectInput>
        </Field>
        <Field label="Status">
          <SelectInput value={params.get("status") ?? ""} onChange={(event) => update({ status: event.target.value || null })}>
            <option value="">Any status</option>
            <option value="unknown">Not reported</option>
            <option value="available">Reported available</option>
            <option value="occupied">Reported occupied</option>
            <option value="paused">Paused</option>
            <option value="offline">Offline</option>
          </SelectInput>
        </Field>
        <div className="flex items-end gap-2">
          <Button type="submit">Search</Button>
          <Button type="button" variant="secondary" onClick={() => update({ favourites: params.get("favourites") === "1" ? null : "1" })}>
            {params.get("favourites") === "1" ? "Showing favourites" : "Favourites only"}
          </Button>
        </div>
      </form>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Button variant={view === "list" ? "primary" : "secondary"} type="button" onClick={() => update({ view: null })}>List</Button>
        <Button variant={view === "map" ? "primary" : "secondary"} type="button" onClick={() => update({ view: "map" })}>Map</Button>
        <Button variant="secondary" type="button" onClick={useLocation}>Use my location</Button>
        {params.get("lat") ? <Button variant="ghost" type="button" onClick={() => update({ lat: null, lon: null })}>Clear location</Button> : null}
      </div>
      {locationError ? <ErrorPanel title="Location was not used" message={locationError} /> : null}
      {query.data?.distance_label ? <p className="my-3 text-sm text-slate-600">Sorted by distance from you.</p> : null}
      {query.isLoading ? <Skeleton className="h-64" /> : null}
      {query.isError ? <ErrorPanel message="The charger list could not be loaded." /> : null}
      {query.data && items.length === 0 ? <EmptyState title="No chargers match" message="Try a different name or status." /> : null}
      {view === "map" ? (
        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <ChargerMap items={items} selectedId={selectedCard?.id ?? null} onSelect={setSelected} />
          <div className="space-y-3">{selectedCard ? <ChargerSummary charger={selectedCard} /> : null}</div>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((charger) => (
            <button key={charger.id} className={`block w-full text-left ${selected === charger.id ? "ring-2 ring-primary rounded-2xl" : ""}`} onClick={() => setSelected(charger.id)}>
              <ChargerSummary charger={charger} />
            </button>
          ))}
        </div>
      )}
      {query.data ? (
        <div className="mt-4">
          <Pagination offset={offset} limit={limit} total={query.data.total} onPage={(next) => update({ offset: String(next) })} />
        </div>
      ) : null}
    </div>
  );
}

function searchQuery(params: URLSearchParams, limit: number, offset: number) {
  const query = new URLSearchParams();
  const q = params.get("q");
  const port = params.get("port");
  const status = params.get("status");
  if (q) query.set("q", q);
  if (port) query.set("port_type", port);
  if (status) query.set("app_status", status);
  if (params.get("favourites") === "1") query.set("favourites_only", "true");
  if (params.get("lat") && params.get("lon")) {
    query.set("latitude", params.get("lat") ?? "");
    query.set("longitude", params.get("lon") ?? "");
  }
  query.set("limit", String(limit));
  query.set("offset", String(offset));
  return query.toString();
}

function ChargerSummary({ charger }: { charger: ChargerCard }) {
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="font-semibold">{charger.display_name}</h2>
        </div>
        <Badge tone={statusTone(charger.app_status)}>{statusLabel(charger.app_status)}</Badge>
      </div>
      <p className="mt-2 text-sm text-slate-600">
        {charger.port_types.length ? charger.port_types.map((item) => item.name).join(", ") : "No connector listed"}
      </p>
      {charger.coordinate_flag !== "ok" ? <p className="mt-1 text-sm text-slate-600">Not shown on the map.</p> : null}
      {charger.straight_line_km != null ? <p className="mt-1 text-sm text-slate-600">{charger.straight_line_km} km away</p> : null}
      {charger.next_estimated_target_at ? <p className="mt-2 text-sm text-primary">Next estimated charging target: {stationTime(charger.next_estimated_target_at, charger.timezone)}. Bay release still needs an unplug report.</p> : null}
      <Link className="mt-3 inline-block text-sm font-semibold text-primary" to={`/app/chargers/${charger.id}`}>View charger</Link>
    </Card>
  );
}

function pin(selected: boolean) {
  const colour = selected ? "#c5a943" : "#0d263e";
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:16px;height:16px;border-radius:999px;background:${colour};border:2px solid white;box-shadow:0 0 0 1px #0d263e"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function Fit({ points }: { points: [number, number][] }) {
  const map = useMap();
  const signature = points.map((point) => point.join(",")).join("|");
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 14);
    else if (points.length > 1) map.fitBounds(points, { padding: [24, 24] });
  }, [map, points, signature]);
  return null;
}

function ChargerMap({ items, selectedId, onSelect }: { items: ChargerCard[]; selectedId: string | null; onSelect: (id: string) => void }) {
  const points = items.filter((item) => item.coordinates_on_map && item.latitude != null && item.longitude != null);
  if (points.length === 0) {
    return <EmptyState title="Nothing to pin on this page" message="Chargers without a valid, consistent coordinate stay in the list and are omitted from the map." />;
  }
  const coords = points.map((item) => [item.latitude as number, item.longitude as number] as [number, number]);
  return (
    <div>
      <div className="h-[420px] overflow-hidden rounded-2xl border border-slate-200">
        <MapContainer center={coords[0]} zoom={13} scrollWheelZoom={false}>
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Fit points={coords} />
          {points.map((item) => (
            <Marker
              key={item.id}
              position={[item.latitude as number, item.longitude as number]}
              icon={pin(item.id === selectedId)}
              eventHandlers={{ click: () => onSelect(item.id) }}
            />
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
