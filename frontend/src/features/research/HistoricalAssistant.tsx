import { useState, type FormEvent } from "react";
import { api, ApiError } from "../../lib/api";
import type { ChargeEstimate, Prediction } from "../../lib/types";
import { Badge, Button, Card, ErrorPanel, Field, TextInput } from "../../components/ui";
import { stationTime } from "../coordination/Updates";

type Preview = { mode: string; warning: boolean; suggest_return_reminder: boolean; remind_at: string; timezone: string; estimate: ChargeEstimate; notice: string };
export function HistoricalAssistant({ scenario }: { scenario: Prediction }) {
  const [capacity,setCapacity]=useState("60"),[current,setCurrent]=useState("40"),[target,setTarget]=useState("80"),[power,setPower]=useState("12"),[lead,setLead]=useState("10");
  const [result,setResult]=useState<Preview|null>(null),[enabled,setEnabled]=useState(false),[pending,setPending]=useState(false),[error,setError]=useState("");
  function change(setter:(value:string)=>void,value:string){setter(value);setResult(null);setEnabled(false);}
  async function submit(e:FormEvent){e.preventDefault();setPending(true);setError("");setEnabled(false);
    try{setResult(await api<Preview>("/research/assistant-preview",{method:"POST",body:{station_key:scenario.station_key,port_type:scenario.port_type,arrival_date:scenario.arrival_local.slice(0,10),arrival_time:scenario.arrival_local.slice(11,16),lead_minutes:Number(lead),plan:{vehicle_id:null,vehicle_label:"Hypothetical car for historical illustration",battery_capacity_kwh:Number(capacity),current_percent:Number(current),target_percent:Number(target),charging_kind:"AC",average_power_kw:Number(power)}}}));}
    catch(e){setError(e instanceof ApiError?e.message:"Could not run the historical assistant illustration.");}finally{setPending(false);}}
  return <Card><div className="flex flex-wrap items-center gap-3"><h2 className="text-lg font-semibold">Elqovanta Charging Assistant — historical demonstration</h2><Badge tone="amber">2020 illustration</Badge></div>
    <p className="mt-2 text-sm text-slate-600">Uses the submitted historical arrival {scenario.arrival_local.replace("T"," ")} ({scenario.timezone}). Battery inputs below are hypothetical calculator inputs; they do not enter or retrain the model.</p>
    <form onSubmit={e=>void submit(e)} className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <Field label="Example capacity (kWh)"><TextInput type="number" min="0.1" max="500" step="0.1" required value={capacity} onChange={e=>change(setCapacity,e.target.value)}/></Field>
      <Field label="Example current battery (%)"><TextInput type="number" min="0" max="100" step="0.1" required value={current} onChange={e=>change(setCurrent,e.target.value)}/></Field>
      <Field label="Example target battery (%)"><TextInput type="number" min="0.1" max="100" step="0.1" required value={target} onChange={e=>change(setTarget,e.target.value)}/></Field>
      <Field label="Example average power (kW)"><TextInput type="number" min="0.1" max="1000" step="0.1" required value={power} onChange={e=>change(setPower,e.target.value)}/></Field>
      <Field label="Example return lead (minutes)"><TextInput type="number" min="1" max="120" step="1" required value={lead} onChange={e=>change(setLead,e.target.value)}/></Field>
      <div className="flex items-end"><Button type="submit" disabled={pending}>{pending?"Calculating…":"Preview historical assistant"}</Button></div>
    </form>
    {error?<div className="mt-3"><ErrorPanel message={error}/></div>:null}
    {result?<div className="mt-4 rounded-xl border border-[#cbded0] bg-[#f1f6ef] p-4"><p className="font-semibold">Estimated {result.estimate.target_percent}% target: {stationTime(result.estimate.estimated_target_at,result.timezone)}</p><p className="mt-2 text-sm">{result.suggest_return_reminder?"This historical model run flags noncharging risk. The assistant would offer an optional reminder before the estimated target.":"This historical model run has no risk warning. A driver could still choose a return reminder."}</p>
      <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={enabled} onChange={e=>setEnabled(e.target.checked)}/>Try enabling the reminder in this illustration</label>
      <p className="mt-2 text-sm font-semibold">{enabled?`Illustrated return time: ${stationTime(result.remind_at,result.timezone)} (${result.timezone})`:"Reminder remains off until the driver chooses it."}</p><p className="mt-3 text-xs text-slate-600">{result.notice} This demonstration does not prove that reminders reduce noncharging time.</p></div>:null}
  </Card>;
}
