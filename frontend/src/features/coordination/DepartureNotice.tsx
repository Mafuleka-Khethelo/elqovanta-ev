import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { ChargerDetail } from "../../lib/types";
import { Card } from "../../components/ui";
import { reportAge, stationTime } from "./Updates";

export function DepartureNotice({chargerId}:{chargerId:string}){
  const charger=useQuery({queryKey:["charger",chargerId],queryFn:()=>api<ChargerDetail>(`/chargers/${chargerId}`),refetchInterval:()=>document.visibilityState==="visible"?8000:false,refetchIntervalInBackground:false});
  const data=charger.data;
  const now=data?new Date(data.server_time).getTime()+Math.max(0,Date.now()-charger.dataUpdatedAt):Date.now();
  const reports=data?.departure_reports.filter(row=>new Date(row.expected_at).getTime()>now)??[];
  if(!data||!reports.length)return null;
  return <Card><h2 className="font-semibold">Expected departures from participants</h2>{reports.map((row,index)=><p key={`${row.reported_at}-${index}`} className="mt-3 text-sm leading-6">A participating driver expects to unplug around <strong>{stationTime(row.expected_at,data.timezone)}</strong> ({data.timezone}) — reported {reportAge(row.reported_at,data.server_time)}.</p>)}<p className="mt-3 text-xs leading-5 text-slate-500">These anonymous reports are voluntary. They are not model predictions, guaranteed departure times or an estimate of when you will get a turn.</p>{charger.isError?<p role="alert" className="mt-2 text-xs text-amber-900">These reports could not be refreshed.</p>:null}</Card>;
}
