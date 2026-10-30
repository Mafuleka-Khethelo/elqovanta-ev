import { HistoricalAssistant } from "./HistoricalAssistant";
import { FormEvent, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ApiError, api } from "../../lib/api";
import type { Insights, ModelCard, Prediction } from "../../lib/types";
import { Button, Card, ErrorPanel, Field, PageHeader, SelectInput, Skeleton, SourceNote, TextInput } from "../../components/ui";
import { PredictionResult } from "./PredictionResult";

export function AboutModelPage() {
  const model = useQuery({ queryKey: ["model-card"], queryFn: () => api<ModelCard>("/research/model") });
  return (
    <div className="space-y-4">
      <PageHeader
        title="About the model"
        lede="This page describes a finished research model. It was trained on Palo Alto charging sessions from before 2019, checked on 2019, and tested on 2020. The website does not retrain it."
      />
      {model.isLoading ? <Skeleton className="h-40" /> : null}
      {model.data && !model.data.ready ? <ErrorPanel title="Prediction is unavailable" message={model.data.reason ?? "The saved model could not be loaded."} /> : null}
      {model.data?.ready ? <ModelReady card={model.data} /> : null}
      {model.data ? <SourceNote>{model.data.limitations}</SourceNote> : null}
    </div>
  );
}

function ModelReady({ card }: { card: ModelCard }) {
  return (
    <>
      <Card>
        <h2 className="font-semibold">What the model estimates</h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          The label is whether a historical session had more than {card.noncharging_threshold_minutes} minutes connected but not charging. Exactly 30 minutes is not a positive case. The warning rule is separate: a warning is shown only when the model probability is greater than {card.warning_cutoff}. A probability of exactly {card.warning_cutoff} is not a warning.
        </p>
        <p className="mt-2 text-sm text-slate-600">Model: {card.model_name}. Time zone of the historical timestamps: {card.timezone}. Artifact: {card.artifact_sha256?.slice(0, 12)}…</p>
        {card.plain_language ? <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-950">{card.plain_language}</p> : null}
        {card.metrics_match_reference === false ? (
          <p className="mt-3 text-sm text-red-800">The evaluation stored in the bundle did not match the project reference. The table below is the stored evaluation, not a replacement result.</p>
        ) : null}
      </Card>
      {card.metrics_table ? (
        <Card>
          <h2 className="mb-3 font-semibold">Stored 2020 test comparison</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr>{["Measure", ...card.metrics_table.columns].map((column) => <th key={column} className="border-b border-slate-200 px-2 py-2">{column}</th>)}</tr>
              </thead>
              <tbody>
                {card.metrics_table.index.map((label, row) => (
                  <tr key={label}>
                    <th className="px-2 py-2 font-medium">{label}</th>
                    {card.metrics_table?.values[row]?.map((value, column) => <td key={`${label}-${column}`} className="px-2 py-2">{value ?? "—"}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
      {card.confusion_matrix ? (
        <Card>
          <h2 className="font-semibold">Stored confusion matrix</h2>
          <p className="mt-1 text-sm text-slate-600">Rows are the actual class, columns are the predicted class, in the order 0 then 1.</p>
          <table className="mt-3 text-sm">
            <tbody>
              {card.confusion_matrix.map((row, index) => (
                <tr key={index}>{row.map((value, column) => <td key={column} className="border border-slate-200 px-4 py-2">{value}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </>
  );
}

export function InsightsPage() {
  const options = useQuery({ queryKey: ["research-options"], queryFn: () => api<{ items: { station_key: string; port_types: string[] }[] }>("/research/options") });
  const [station, setStation] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [applied, setApplied] = useState({ station: "", start: "", end: "" });
  const insights = useQuery({
    queryKey: ["insights", applied],
    queryFn: () => {
      const query = new URLSearchParams();
      if (applied.station) query.set("station_key", applied.station);
      if (applied.start && applied.end) {
        query.set("start_date", applied.start);
        query.set("end_date", applied.end);
      }
      return api<Insights>(`/research/insights?${query.toString()}`);
    },
  });

  function apply(event: FormEvent) {
    event.preventDefault();
    setApplied({ station, start, end });
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Historical insights" lede="These charts use the frozen Palo Alto history supplied with the saved model. They are not the charging sessions recorded in this website, and charger names at the same coordinates are not treated as one physical site." />
      <form className="grid gap-3 md:grid-cols-4" onSubmit={apply}>
        <Field label="Historical charger">
          <SelectInput value={station} onChange={(event) => setStation(event.target.value)}>
            <option value="">All charger names</option>
            {options.data?.items.map((item) => <option key={item.station_key} value={item.station_key}>{item.station_key}</option>)}
          </SelectInput>
        </Field>
        <Field label="Start date"><TextInput type="date" value={start} onChange={(event) => setStart(event.target.value)} /></Field>
        <Field label="End date"><TextInput type="date" value={end} onChange={(event) => setEnd(event.target.value)} /></Field>
        <div className="flex items-end"><Button type="submit">Apply filters</Button></div>
      </form>
      {insights.isLoading ? <Skeleton className="h-40" /> : null}
      {insights.isError ? <ErrorPanel message={insights.error instanceof ApiError ? insights.error.message : "Historical insights are unavailable."} /> : null}
      {insights.data ? <InsightBody data={insights.data} /> : null}
    </div>
  );
}

function InsightBody({ data }: { data: Insights }) {
  const hourMax = Math.max(1, ...data.arrivals_by_hour.map((item) => item.count));
  return (
    <>
      <SourceNote>{data.source} {data.time_basis} Sample size: {data.session_count} sessions.</SourceNote>
      <div className="grid gap-3 md:grid-cols-4">
        <Card><p className="text-sm text-slate-500">Sessions</p><p className="text-2xl font-semibold">{data.session_count}</p></Card>
        <Card><p className="text-sm text-slate-500">Over 30 minutes not charging</p><p className="text-2xl font-semibold">{data.long_noncharging_percent ?? "—"}%</p><p className="text-xs text-slate-500">{data.long_noncharging_count} sessions</p></Card>
        <Card><p className="text-sm text-slate-500">Median connected minutes</p><p className="text-2xl font-semibold">{data.median_connected_minutes ?? "—"}</p></Card>
        <Card><p className="text-sm text-slate-500">Median charging / not charging</p><p className="text-2xl font-semibold">{data.median_charging_minutes ?? "—"} / {data.median_noncharging_minutes ?? "—"}</p></Card>
      </div>
      <Card>
        <h2 className="font-semibold">Arrivals by hour</h2>
        <p className="text-xs text-slate-500">Each bar is a count of sessions, not a percentage.</p>
        <div className="mt-3 flex h-40 items-end gap-1">
          {data.arrivals_by_hour.map((item) => (
            <div key={item.hour} className="flex flex-1 flex-col items-center justify-end">
              <div className="w-full rounded-t bg-teal" style={{ height: `${(item.count / hourMax) * 100}%` }} title={`${item.hour}:00 · ${item.count}`} />
              {item.hour % 3 === 0 ? <span className="mt-1 text-[10px] text-slate-500">{item.hour}</span> : <span className="mt-1 text-[10px] text-transparent">0</span>}
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <h2 className="mb-3 font-semibold">Arrivals by weekday</h2>
        <BarList items={data.arrivals_by_weekday.map((item) => ({ label: item.weekday, value: item.count, note: `${item.count} sessions` }))} />
      </Card>
      <Card>
        <h2 className="font-semibold">Long noncharging rate by charger name</h2>
        <p className="mb-3 text-xs text-slate-500">The percentage is the share of that name’s sessions over 30 minutes. The count beside it is the sample size. This is not a ranking of physical sites.</p>
        <BarList items={data.chargers.map((item) => ({ label: item.station_key, value: item.long_noncharging_percent, note: `${item.long_noncharging_percent}% of ${item.session_count}` }))} />
      </Card>
    </>
  );
}

function BarList({ items }: { items: { label: string; value: number; note: string }[] }) {
  const max = Math.max(1, ...items.map((item) => item.value));
  if (items.length === 0) return <p className="text-sm text-slate-600">No rows in this filter.</p>;
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.label}>
          <div className="flex justify-between gap-3 text-sm"><span className="truncate">{item.label}</span><span>{item.note}</span></div>
          <div className="mt-1 h-2 rounded bg-slate-200"><div className="h-2 rounded bg-primary" style={{ width: `${(item.value / max) * 100}%` }} /></div>
        </li>
      ))}
    </ul>
  );
}

export function PredictionLabPage() {
  const [params] = useSearchParams();
  const options = useQuery({ queryKey: ["research-options"], queryFn: () => api<{ items: { station_key: string; port_types: string[] }[]; timezone: string; arrival_year: number }>("/research/options") });
  const [station, setStation] = useState(params.get("station") ?? "");
  const [port, setPort] = useState(params.get("port") ?? "");
  const [date, setDate] = useState(params.get("date") ?? "2020-06-15");
  const [time, setTime] = useState("08:00");
  const [runs, setRuns] = useState<Prediction[]>([]);
  const ports = useMemo(() => options.data?.items.find((item) => item.station_key === station)?.port_types ?? [], [options.data, station]);
  const predict = useMutation({
    mutationFn: (body: { station_key: string; port_type: string; arrival_date: string; arrival_time: string }) => api<Prediction>("/research/predict", {
      method: "POST",
      body,
    }),
    onSuccess: (result) => setRuns((previous) => [result, ...previous].slice(0, 5)),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    predict.mutate({ station_key: station, port_type: port || ports[0], arrival_date: date, arrival_time: time });
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Historical Prediction Lab"
        lede="Run the saved Random Forest with different chargers, ports and arrival dates, then compare all 24 arrival hours. Results use frozen 2020 research scenarios, not today's charger availability."
      />
      {options.isError ? <ErrorPanel title="The lab is unavailable" message={options.error instanceof ApiError ? options.error.message : "The saved model is not ready."} /> : null}
      <form onSubmit={onSubmit}>
        <fieldset disabled={predict.isPending} className="grid gap-3 md:grid-cols-2">
        <Field label="Historical charger name">
          <SelectInput required value={station} onChange={(event) => { setStation(event.target.value); setPort(""); }}>
            <option value="">Choose a charger name</option>
            {options.data?.items.map((item) => <option key={item.station_key} value={item.station_key}>{item.station_key}</option>)}
          </SelectInput>
        </Field>
        <Field label="Observed port type">
          <SelectInput required value={port || ports[0] || ""} onChange={(event) => setPort(event.target.value)}>
            {ports.map((name) => <option key={name} value={name}>{name}</option>)}
          </SelectInput>
        </Field>
        <Field label="Arrival date in 2020" hint="1 January to 31 December 2020.">
          <TextInput type="date" required min="2020-01-01" max="2020-12-31" value={date} onChange={(event) => setDate(event.target.value)} />
        </Field>
        <Field label="Local arrival time" hint="Palo Alto local time. Only the hour is a model feature; changing minutes alone will not change the probability.">
          <TextInput type="time" required value={time} onChange={(event) => setTime(event.target.value)} />
        </Field>
        <Button type="submit" disabled={predict.isPending || !options.data || !station}>{predict.isPending ? "Running the saved model…" : "Run historical prediction"}</Button>
        </fieldset>
      </form>
      {predict.isError ? <ErrorPanel message={predict.error instanceof ApiError ? predict.error.message : "Prediction failed."} /> : null}
      {predict.isPending ? <Skeleton className="h-40" /> : null}
      {predict.data && !predict.isPending ? <Card><p className="mb-4 text-sm text-slate-600">Results for {predict.data.station_key} · submitted arrival {predict.data.arrival_local.replace("T", " ")}</p><PredictionResult key={predict.data.computed_at} result={predict.data} /></Card> : null}
      {predict.data && !predict.isPending ? <HistoricalAssistant key={`assistant-${predict.data.computed_at}`} scenario={predict.data} /> : null}
      {runs.length ? (
        <Card>
          <h2 className="font-semibold">Compare your model runs</h2>
          <p className="mt-1 text-sm text-slate-600">The last five successful submissions in this visit. Change an input above and run again to add a comparison. Selecting an hourly bar inspects the existing run.</p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr>{["Charger / port", "Submitted arrival", "Probability", "Warning", "Change from previous run"].map((label) => <th key={label} className="border-b px-2 py-2">{label}</th>)}</tr></thead>
              <tbody>{runs.map((run, index) => {
                const previous = runs[index + 1];
                const difference = previous ? (run.probability - previous.probability) * 100 : null;
                return <tr key={`${run.computed_at}-${index}`}><td className="px-2 py-3">{run.station_key}<span className="block text-xs text-slate-500">{run.port_type}</span></td><td className="px-2 py-3 whitespace-nowrap">{run.arrival_local.replace("T", " ")}</td><td className="px-2 py-3 font-semibold">{(run.probability * 100).toFixed(2)}%</td><td className="px-2 py-3">{run.warning ? "Yes" : "No"}</td><td className="px-2 py-3">{difference == null ? "First run shown" : `${difference >= 0 ? "+" : ""}${difference.toFixed(2)} percentage points`}</td></tr>;
              })}</tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
