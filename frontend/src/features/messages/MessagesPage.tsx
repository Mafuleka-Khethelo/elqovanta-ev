import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api, newRequestKey } from "../../lib/api";
import type { ChatMessage, ConversationSummary } from "../../lib/types";
import { formatWhen } from "../../lib/format";
import { Button, EmptyState, ErrorPanel, PageHeader, TextArea } from "../../components/ui";
import { useAuth } from "../../app/providers";
import { useOffline } from "../coordination/Updates";

export function MessagesPage() {
  const { user } = useAuth();
  const { conversationId } = useParams();
  const threads = useQuery({
    queryKey: ["conversations"],
    enabled: user?.role !== "researcher",
    queryFn: () => api<{ items: ConversationSummary[] }>("/conversations"),
    refetchInterval: () => (document.visibilityState === "visible" && !conversationId ? 8000 : false),
    refetchIntervalInBackground: false,
  });

  if (user?.role === "researcher") return <ErrorPanel title="Private messages are restricted" message="Examiner access does not grant access to driver and station-manager conversations." />;
  return (
    <div>
      <PageHeader title="Messages" />
      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-2">
          {threads.data?.items.length === 0 ? <p className="text-sm text-slate-600">No conversations yet. Open a charger and choose Message the manager.</p> : null}
          {threads.data?.items.map((item) => (
            <Link key={item.id} to={`/app/messages/${item.id}`} className={`block rounded-xl border px-3 py-3 text-sm ${item.id === conversationId ? "border-primary bg-blue-50" : "border-slate-200 bg-white"}`}>
              <span className="flex items-center justify-between gap-2">
                <strong>{item.charger_name}</strong>
                {item.unread ? <span className="rounded-full bg-teal px-2 text-xs text-white">{item.unread}</span> : null}
              </span>
              <span className="mt-1 block text-slate-500">{item.other_name}</span>
              {item.last_body ? <span className="mt-1 block truncate text-slate-600">{item.last_body}</span> : null}
            </Link>
          ))}
        </aside>
        {conversationId ? <Thread key={conversationId} conversationId={conversationId} /> : <EmptyState title="Choose a conversation" message="Select a thread to read and send messages." />}
      </div>
    </div>
  );
}

function Thread({ conversationId }: { conversationId: string }) {
  const offline = useOffline();
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [sent, setSent] = useState(false);
  const [requestId, setRequestId] = useState(() => newRequestKey());
  const [before, setBefore] = useState<string | null>(null);
  const [older, setOlder] = useState<ChatMessage[]>([]);
  const messages = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => api<{ items: ChatMessage[]; has_older: boolean }>(`/conversations/${conversationId}/messages`),
    refetchInterval: () => (document.visibilityState === "visible" ? 4000 : false),
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    void api(`/conversations/${conversationId}/read`, { method: "POST" }).then(() => queryClient.invalidateQueries({ queryKey: ["conversations"] })).catch(() => setError("The read marker could not be saved. Your messages are unchanged."));
  }, [conversationId, messages.data?.items.at(-1)?.id, queryClient]);

  async function loadOlder() {
    const oldest = older[0]?.created_at ?? messages.data?.items[0]?.created_at;
    if (!oldest) return;
    setLoadingOlder(true);
    try {
      const page = await api<{ items: ChatMessage[]; has_older: boolean }>(`/conversations/${conversationId}/messages?before=${encodeURIComponent(oldest)}`);
      setOlder((current) => [...page.items, ...current].filter((item,index,all) => all.findIndex(other=>other.id===item.id)===index));
      setBefore(page.has_older ? oldest : "end");
    } catch { setError("Older messages could not be loaded. Please try again."); }
    finally { setLoadingOlder(false); }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setSent(false);
    setError(null);
    try {
      await api(`/conversations/${conversationId}/messages`, {
        method: "POST",
        body: { body, client_request_id: requestId },
      });
      setBody("");
      setSent(true);
      setRequestId(newRequestKey());
      await queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The message was not sent. You can try again with the same request.");
    } finally { setPending(false); }
  }

  const visible = [...older, ...(messages.data?.items ?? [])].filter((item,index,all)=>all.findIndex(other=>other.id===item.id)===index);
  const hasOlder = before !== "end" && (messages.data?.has_older || older.length > 0);

  return (
    <section className="flex min-h-[420px] flex-col rounded-2xl border border-slate-200 bg-white">
      <div className="flex-1 space-y-3 p-4">
        {messages.data?.has_older || older.length ? (
          <Button variant="ghost" type="button" onClick={() => void loadOlder()} disabled={loadingOlder || before === "end"}>
            {hasOlder ? "Load older messages" : "No older messages"}
          </Button>
        ) : null}
        {visible.map((message) => (
          <article key={message.id} className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${message.mine ? "ml-auto bg-blue-50" : "bg-slate-100"}`}>
            <p className="text-xs text-slate-500">{message.sender_name} · {formatWhen(message.created_at)}</p>
            <p className="mt-1 whitespace-pre-wrap break-words">{message.body}</p>
          </article>
        ))}
        {visible.length === 0 ? <p className="text-sm text-slate-500">No messages in this conversation yet.</p> : null}
      </div>
      <form className="border-t border-slate-200 p-4" onSubmit={(event) => void onSubmit(event)}>
        {error ? <div className="mb-2"><ErrorPanel message={error} /></div> : null}
        {messages.isError || messages.isPaused || offline ? <p role="alert" className="mb-3 text-sm text-amber-900">This conversation could not be refreshed. Last known messages are shown.</p> : null}
        <div className="mb-3 flex flex-wrap gap-2" aria-label="Editable message starters">{["I need help with this charger", "I expect to leave soon", "Is access to the charger clear?"].map(text=><button key={text} type="button" disabled={pending} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-primary" onClick={()=>{setBody(text);setRequestId(newRequestKey());setSent(false);document.getElementById("message-body")?.focus();}}>{text}</button>)}</div>
        <label className="block text-sm font-medium" htmlFor="message-body">Message</label>
        <TextArea id="message-body" rows={3} required maxLength={2000} disabled={pending} value={body} onChange={(event) => {setBody(event.target.value);setRequestId(newRequestKey());setSent(false);}} />
        <div className="mt-2 flex items-center gap-3"><Button type="submit" disabled={pending||messages.isError||messages.isPaused||offline||!body.trim()}>{pending?"Sending…":error?"Retry send":"Send"}</Button>{sent?<span role="status" className="text-xs text-primary">Sent</span>:null}</div>
      </form>
    </section>
  );
}
