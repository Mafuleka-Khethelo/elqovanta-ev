import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api";
import { Button, Card, ErrorPanel, Field, PageHeader, SelectInput, SourceNote, TextInput } from "../../components/ui";
import { formatWhen } from "../../lib/format";

type DemoOption = { id: string; display_name: string; context: {arrival_local: string; expires_at: string; port_type: string} | null };

export function DemonstrationPage() {
  const client = useQueryClient();
  const options = useQuery({queryKey:["research-options"],queryFn:()=>api<{items:{station_key:string;port_types:string[]}[]}>("/research/options")});
  const drivers = useQuery({queryKey:["demonstration-options"],queryFn:()=>api<{items:DemoOption[]}>("/research/demonstrations")});
  const [driver,setDriver]=useState("");
  const [station,setStation]=useState("");
  const [port,setPort]=useState("");
  const [date,setDate]=useState("2020-06-15");
  const [time,setTime]=useState("22:00");
  const [pending,setPending]=useState(false);
  const [error,setError]=useState("");
  const [success,setSuccess]=useState("");
  const ports=options.data?.items.find(item=>item.station_key===station)?.port_types??[];
  useEffect(()=>{if(!ports.includes(port))setPort(ports[0]??"");},[station, options.data, port]);

  async function run(event:FormEvent){
    event.preventDefault();setPending(true);setError("");setSuccess("");
    try{await api("/research/demonstrations",{method:"POST",body:{driver_id:driver,station_key:station,port_type:port,arrival_date:date,arrival_time:time}});await client.invalidateQueries({queryKey:["demonstration-options"]});setSuccess("Historical example selected. Sign in separately as that labelled demonstration driver and open the selected charger. No operational session has been backdated.");}
    catch(caught){setError(caught instanceof ApiError?caught.message:"The demonstration could not be configured.");}finally{setPending(false);}
  }
  async function clear(id:string){setPending(true);setError("");setSuccess("");try{await api(`/research/demonstrations/${id}`,{method:"DELETE"});await drivers.refetch();setSuccess("The historical demonstration context was cleared.");}catch(caught){setError(caught instanceof ApiError?caught.message:"Could not clear the context.");}finally{setPending(false);}}

  return <div className="space-y-5"><PageHeader title="Driver demonstration" lede="Choose a supported historical example for a labelled demonstration driver. Ordinary current sessions receive no model forecast." /><SourceNote>Examiner workspace. This selects only a 2020 assistant context and expires after eight hours. It grants no access to the driver's private messages or station operations. Repeated reads and queue updates do not rerun the model.</SourceNote>{error||options.isError||drivers.isError?<ErrorPanel message={error||"Demonstration options are unavailable. Check model readiness and your connection."}/>:null}{success?<p role="status" className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm leading-6">{success}</p>:null}<Card><form onSubmit={event=>void run(event)} className="grid gap-4 md:grid-cols-2" aria-busy={pending}><Field label="Labelled demonstration driver"><SelectInput required value={driver} onChange={event=>setDriver(event.target.value)}><option value="">Choose a demonstration driver</option>{drivers.data?.items.map(item=><option key={item.id} value={item.id}>{item.display_name}</option>)}</SelectInput></Field><Field label="Exact historical charger"><SelectInput required value={station} onChange={event=>setStation(event.target.value)}><option value="">Choose a supported charger</option>{options.data?.items.map(item=><option key={item.station_key} value={item.station_key}>{item.station_key}</option>)}</SelectInput></Field><Field label="Observed port type"><SelectInput required value={port} onChange={event=>setPort(event.target.value)}><option value="">Choose a port</option>{ports.map(item=><option key={item} value={item}>{item}</option>)}</SelectInput></Field><Field label="Historical arrival date"><TextInput type="date" min="2020-01-01" max="2020-12-31" required value={date} onChange={event=>setDate(event.target.value)}/></Field><Field label="Palo Alto local arrival time"><TextInput type="time" required value={time} onChange={event=>setTime(event.target.value)}/></Field><div className="flex items-end"><Button type="submit" disabled={pending||!driver||!station||!port||options.isError}>{pending?"Saving…":"Select historical example"}</Button></div></form></Card><section className="space-y-3"><h2 className="text-lg font-semibold">Configured demonstration drivers</h2>{drivers.data?.items.length===0?<SourceNote>No labelled drivers exist. Run the documented local seed command first.</SourceNote>:null}{drivers.data?.items.map(item=><Card key={item.id}><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold">{item.display_name}</h3><p className="mt-1 text-sm text-slate-600">{item.context?`${item.context.arrival_local.replace("T"," ")} · ${item.context.port_type} · expires ${formatWhen(item.context.expires_at)}`:"No historical demonstration selected."}</p></div>{item.context?<Button variant="secondary" disabled={pending} onClick={()=>void clear(item.id)}>Clear context</Button>:null}</div></Card>)}</section></div>;
}
