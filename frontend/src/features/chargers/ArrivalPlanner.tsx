import { useState } from "react";
import { Clock3 } from "lucide-react";
import { ApiError } from "../../lib/api";
import type { ChargerDetail } from "../../lib/types";
import { Button, Field, SelectInput, TextInput } from "../../components/ui";
import { AdvisoryResult, useChargingAdvisory } from "./ChargerGuidance";
import { stationDateTimeInput } from "./arrival";

export function ArrivalPlanner({ charger, portType, onPortChange, offline }: { charger: ChargerDetail; portType: string; onPortChange: (port: string) => void; offline: boolean }) {
  const [later, setLater] = useState(false);
  const [input, setInput] = useState(() => stationDateTimeInput(new Date(charger.server_time).getTime() + 3600000, charger.timezone));
  const [checked, setChecked] = useState("");
  const advisory = useChargingAdvisory(charger.id, portType || null, undefined, !later || !!checked, later ? checked || undefined : undefined);
  const baseTime = new Date(charger.server_time).getTime();
  return <section className="ev-arrival-planner" aria-labelledby="arrival-title">
    <header><div><span className="ev-arrival-icon"><Clock3 size={21} /></span><h2 id="arrival-title">When will you arrive?</h2></div><span className="ev-arrival-auto">Automatic charging advisory</span></header>
    <div className="ev-arrival-grid">
      <div className="ev-arrival-controls">
        <div className="ev-arrival-toggle" role="group" aria-label="Arrival time"><Button variant={later ? "secondary" : "primary"} aria-pressed={!later} onClick={() => { setLater(false); setChecked(""); }}>Now</Button><Button variant={later ? "primary" : "secondary"} aria-pressed={later} onClick={() => { setLater(true); setChecked(""); }}>Later</Button></div>
        {charger.port_types.length > 1 ? <Field label="Port type"><SelectInput value={portType} onChange={event => onPortChange(event.target.value)}><option value="">Choose a port type</option>{charger.port_types.map(port => <option key={port.name} value={port.name}>{port.name}</option>)}</SelectInput></Field> : <span className="ev-arrival-port">{charger.port_types[0]?.name ?? "No port types listed"}</span>}
        {later ? <form onSubmit={event => { event.preventDefault(); if (checked === input) void advisory.refetch(); else setChecked(input); }} className="space-y-3">
          <Field label="Planned arrival" hint={`Station time · ${charger.timezone}`}><TextInput type="datetime-local" required min={stationDateTimeInput(baseTime + 60000, charger.timezone)} max={stationDateTimeInput(baseTime + 7 * 86400000, charger.timezone)} value={input} onChange={event => { setInput(event.target.value); setChecked(""); }} /></Field>
          <Button type="submit" disabled={offline || !input || advisory.isFetching || (charger.port_types.length > 1 && !portType)}>Check arrival</Button>
          <span className="ev-arrival-hint">Choose a time within the next 7 days.</span>
        </form> : <span className="ev-arrival-hint">Checked automatically for your current arrival.</span>}
      </div>
      <div className="ev-arrival-result">
        {later && !checked ? <div className="ev-arrival-placeholder"><Clock3 size={24} /><strong>See the advisory for your arrival</strong><span>Choose a date, time and port, then check your arrival.</span></div> : <AdvisoryResult data={advisory.data} loading={advisory.isFetching} error={offline ? "You are offline. Reconnect to check your arrival." : advisory.isError ? advisory.error instanceof ApiError ? advisory.error.message : "Could not check this arrival. Please try again." : undefined} />}
      </div>
    </div>
    <footer>Planning does not reserve a bay or join the waiting list. We check the actual time again when you start charging.</footer>
  </section>;
}
