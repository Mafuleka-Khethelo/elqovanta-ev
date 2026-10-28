import { useState } from "react";
import type { Prediction } from "../../lib/types";
import { Badge, Button, SourceNote } from "../../components/ui";

const hourLabel = (hour: number) => `${String(hour).padStart(2, "0")}:00`;
const percent = (probability: number) => `${(probability * 100).toFixed(2)}%`;

export function PredictionResult({ result }: { result: Prediction }) {
  const [hour, setHour] = useState(result.derived_features.arrival_hour);
  const selected = result.hourly.find((item) => item.arrival_hour === hour)!;
  const lowest = result.hourly.reduce((a, b) => a.probability <= b.probability ? a : b);
  const highest = result.hourly.reduce((a, b) => a.probability >= b.probability ? a : b);
  const cutoff = result.warning_cutoff * 100;
  const date = result.arrival_local.slice(0, 10);
  const difference = (selected.probability - result.probability) * 100;
  const inputs = [
    ["Station Name", result.station_key],
    ["Port Type", result.port_type],
    ["arrival_hour", hour],
    ["arrival_day", result.derived_features.arrival_day],
    ["arrival_month", result.derived_features.arrival_month],
    ["station_sessions_30d", result.station_sessions_30d],
    ["station_long_rate_30d", result.station_long_rate_30d == null ? "Missing (no earlier sessions)" : result.station_long_rate_30d.toFixed(6)],
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4" aria-live="polite" aria-atomic="true">
        <div>
          <p className="text-sm font-semibold text-slate-600">{date} · {result.derived_features.arrival_day} · {hourLabel(hour)} · {result.port_type}</p>
          <p className="mt-2 text-5xl font-semibold tracking-tight text-navy">{percent(selected.probability)}</p>
          <p className="mt-2 max-w-xl text-sm text-slate-700">Estimated probability of more than {result.noncharging_threshold_minutes} minutes connected without charging.</p>
          {hour !== result.derived_features.arrival_hour ? <p className="mt-1 text-sm text-slate-600">{difference >= 0 ? "+" : ""}{difference.toFixed(2)} percentage points compared with the submitted arrival at {result.arrival_local.slice(11, 16)}.</p> : null}
        </div>
        <Badge tone={selected.warning ? "amber" : "blue"}>{selected.warning ? "Warning" : "No warning"} · {selected.warning ? "above" : "at or below"} {cutoff}% cutoff</Badge>
      </div>

      <div>
        <h3 className="font-semibold">Compare arrival hours</h3>
        <p className="mt-1 text-sm text-slate-600">All 24 bars are predictions from this model run. Select an hour to inspect its result. Time zone: {result.timezone}.</p>
        <div className="mt-4 flex gap-2">
          <div className="flex h-44 flex-col justify-between text-xs text-slate-500"><span>100%</span><span>0%</span></div>
          <div className="min-w-0 flex-1 overflow-x-auto pb-2">
            <div className="min-w-[480px]">
              <div className="relative flex h-44 items-end gap-1 border-b border-slate-300 bg-slate-50">
                <div className="pointer-events-none absolute right-0 left-0 z-10 border-t border-dashed border-amber-700" style={{ bottom: `${cutoff}%` }} />
                {result.hourly.map((item) => (
                  <button
                    key={item.arrival_hour}
                    type="button"
                    className={`relative flex h-full flex-1 items-end rounded-t hover:bg-slate-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy ${hour === item.arrival_hour ? "bg-slate-200 ring-2 ring-navy" : ""}`}
                    aria-label={`${hourLabel(item.arrival_hour)}: ${percent(item.probability)}, ${item.warning ? "warning" : "no warning"}`}
                    aria-pressed={hour === item.arrival_hour}
                    title={`${hourLabel(item.arrival_hour)}: ${percent(item.probability)}`}
                    onClick={() => setHour(item.arrival_hour)}
                  >
                    <span className={`block w-full rounded-t ${item.warning ? "bg-gold" : "bg-primary"}`} style={{ height: `${item.probability * 100}%`, minHeight: "2px" }} />
                  </button>
                ))}
              </div>
              <div className="mt-1 flex gap-1 text-center text-[10px] text-slate-500" aria-hidden="true">
                {result.hourly.map((item) => <span key={item.arrival_hour} className="flex-1">{String(item.arrival_hour).padStart(2, "0")}</span>)}
              </div>
            </div>
          </div>
        </div>
        <p className="mt-1 text-xs text-slate-600">Dashed line: {cutoff}% warning cutoff. Gold bars cross it. Scale: 0–100%.</p>
        <label className="mt-4 block text-sm font-medium">
          Selected arrival hour: {hourLabel(hour)}
          <input className="mt-2 block w-full accent-[#142c43]" type="range" min="0" max="23" step="1" value={hour} onChange={(event) => setHour(Number(event.target.value))} />
        </label>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setHour(lowest.arrival_hour)}>Lowest score: {hourLabel(lowest.arrival_hour)} · {percent(lowest.probability)}</Button>
          <Button variant="secondary" onClick={() => setHour(highest.arrival_hour)}>Highest score: {hourLabel(highest.arrival_hour)} · {percent(highest.probability)}</Button>
        </div>
      </div>

      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        <div><dt className="text-slate-500">Earlier sessions in the 30-day window</dt><dd className="mt-1 text-xl font-semibold">{result.station_sessions_30d}</dd></div>
        <div><dt className="text-slate-500">Earlier sessions over 30 minutes</dt><dd className="mt-1 text-xl font-semibold">{result.station_long_rate_30d == null ? "No earlier sessions" : percent(result.station_long_rate_30d)}</dd></div>
        <div><dt className="text-slate-500">Last computed</dt><dd className="mt-1">{new Date(result.computed_at).toLocaleString()}</dd></div>
      </dl>
      <details className="rounded-xl border border-slate-200 p-3 text-sm">
        <summary className="cursor-pointer font-semibold">Show the seven model inputs</summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr><th className="border-b px-2 py-2">Feature</th><th className="border-b px-2 py-2">Value for the selected hour</th></tr></thead>
            <tbody>{inputs.map(([name, value]) => <tr key={name}><th className="px-2 py-2 font-medium">{name}</th><td className="px-2 py-2">{value}</td></tr>)}</tbody>
          </table>
        </div>
        <p className="mt-3 text-slate-600">History: {result.history_window_start} inclusive to {result.history_window_end_exclusive} exclusive. The entire arrival day is excluded.</p>
        <p className="mt-2 text-slate-600">Model: {result.model_name}. Artifact: <span className="break-all font-mono text-xs">{result.artifact_sha256}</span></p>
        <p className="mt-2 text-slate-600">Selected probability before display rounding: {selected.probability.toPrecision(12)}. The model uses the arrival hour; minutes and login details are not features.</p>
      </details>
      <SourceNote>Changing an input can change the result. Re-running the same inputs should reproduce the same probability to numerical precision; signing in again does not change the model inputs. {result.limitations}</SourceNote>
    </div>
  );
}
