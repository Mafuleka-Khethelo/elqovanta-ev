import { useRef, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, newRequestKey } from "../../lib/api";
import { formatWhen } from "../../lib/format";
import { Badge, Button, Card, ErrorPanel, Field, Pagination, SelectInput, Skeleton, SourceNote, TextArea } from "../../components/ui";
import { useOffline } from "./Updates";

type Report={id:string;category:string;details:string;state:string;manager_response:string|null;created_at:string;updated_at:string};

export function HelpReports({chargerId,manager=false}:{chargerId:string;manager?:boolean}){
  const client=useQueryClient();
  const offline=useOffline();
  const [offset,setOffset]=useState(0);
  const [category,setCategory]=useState("not_working");
  const [details,setDetails]=useState("");
  const [showForm,setShowForm]=useState(false);
  const [pending,setPending]=useState(false);
  const [error,setError]=useState("");
  const [success,setSuccess]=useState("");
  const key=useRef(newRequestKey());
  const reports=useQuery({queryKey:["help-reports",manager,chargerId,offset],queryFn:()=>api<{items:Report[];total:number}>(`${manager?"/manager":""}/chargers/${chargerId}/reports?limit=5&offset=${offset}`),refetchInterval:()=>document.visibilityState==="visible"?10000:false,refetchIntervalInBackground:false});
  async function submit(event:FormEvent){event.preventDefault();setPending(true);setError("");setSuccess("");try{await api(`/chargers/${chargerId}/reports`,{method:"POST",body:{category,details,idempotency_key:key.current}});key.current=newRequestKey();setDetails("");setShowForm(false);setOffset(0);await client.invalidateQueries({queryKey:["help-reports"]});setSuccess("Your private report was sent.");}catch(caught){setError(caught instanceof ApiError?caught.message:"The report was not confirmed. Retry with the same details.");}finally{setPending(false);}}
  return <Card><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold">{manager?"Private driver help reports":"Quick help"}</h2>{!manager?<div className="flex flex-wrap gap-2">{[["not_working","Charger not working"],["access_blocked","Access blocked"]].map(([value,label])=><Button key={value} variant="secondary" onClick={()=>{setCategory(value);setShowForm(true);key.current=newRequestKey();}}>{label}</Button>)}</div>:null}</div>{error?<div className="mt-3"><ErrorPanel message={error}/></div>:null}{success?<p role="status" className="mt-3 rounded-lg bg-green-50 p-3 text-sm leading-6">{success}</p>:null}{showForm&&!manager?<form className="mt-4 space-y-3" onSubmit={event=>void submit(event)} aria-busy={pending}><Field label="Issue"><SelectInput disabled={pending||offline} value={category} onChange={event=>{setCategory(event.target.value);key.current=newRequestKey();}}><option value="not_working">Charger not working</option><option value="access_blocked">Access blocked</option></SelectInput></Field><Field label="Describe what you found" hint="Visible only to you and assigned station managers."><TextArea rows={3} required minLength={3} maxLength={1000} disabled={pending||offline} value={details} onChange={event=>{setDetails(event.target.value);key.current=newRequestKey();}}/></Field><div className="flex gap-2"><Button type="submit" disabled={pending||offline}>{pending?"Sending…":"Send private report"}</Button><Button type="button" variant="secondary" disabled={pending||offline} onClick={()=>setShowForm(false)}>Cancel</Button></div></form>:null}<details className="ev-details-note"><summary>About private reports</summary><p>Visible to you and assigned managers. A report does not automatically change public station status.</p></details>{reports.isLoading?<Skeleton className="mt-4 h-20"/>:null}{reports.isError?<div className="mt-3"><ErrorPanel message="Help reports could not be refreshed. Please try again."/><Button className="mt-2" variant="secondary" onClick={()=>void reports.refetch()}>Refresh reports</Button></div>:null}{reports.data?.items.length===0?<div className="mt-4"><SourceNote>{manager?"No help reports for this charger yet.":"You have not submitted any help reports for this charger."}</SourceNote></div>:null}<div className="mt-4 space-y-3">{reports.data?.items.map(row=><article key={row.id} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-semibold">{row.category==="not_working"?"Charger not working":"Access blocked"}</h3><Badge tone={row.state==="resolved"?"teal":"amber"}>{row.state}</Badge></div><p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">{row.details}</p><p className="mt-2 text-xs text-slate-500">Reported {formatWhen(row.created_at)}</p>{row.manager_response?<p className="mt-3 whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-sm leading-6"><strong>Manager response:</strong> {row.manager_response}</p>:null}{manager&&row.state!=="resolved"?<ReportResponse row={row} disabled={(reports.isError||reports.isPaused||offline)}/>:null}</article>)}</div>{reports.data&&reports.data.total>5?<div className="mt-4"><Pagination offset={offset} limit={5} total={reports.data.total} onPage={setOffset}/></div>:null}</Card>;
}

function ReportResponse({row,disabled}:{row:Report;disabled:boolean}){
  const client=useQueryClient();
  const [response,setResponse]=useState(row.manager_response??"");
  const [state,setState]=useState("acknowledged");
  const [pending,setPending]=useState(false);
  const [error,setError]=useState("");
  async function submit(event:FormEvent){event.preventDefault();setPending(true);setError("");try{await api(`/manager/reports/${row.id}`,{method:"PATCH",body:{state,response}});await client.invalidateQueries({queryKey:["help-reports"]});}catch(caught){setError(caught instanceof ApiError?caught.message:"Could not update this report.");}finally{setPending(false);}}
  return <form className="mt-4 space-y-3" onSubmit={event=>void submit(event)}>{error?<ErrorPanel message={error}/>:null}<Field label="Private update to the reporter"><TextArea rows={2} required minLength={3} maxLength={1000} value={response} onChange={event=>setResponse(event.target.value)} disabled={pending||disabled}/></Field><div className="flex flex-wrap items-end gap-3"><Field label="Report status"><SelectInput value={state} onChange={event=>setState(event.target.value)} disabled={pending||disabled}><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option></SelectInput></Field><Button type="submit" disabled={pending||disabled}>{pending?"Saving…":"Send private update"}</Button></div></form>;
}
