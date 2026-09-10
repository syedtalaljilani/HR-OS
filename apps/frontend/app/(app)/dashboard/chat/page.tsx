"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import Button from "@/app/hr/_components/Button";
import { inputClass } from "@/app/hr/_components/Field";
import { EmptyState } from "@/app/hr/_components/Modal";

import {
  draftEmailWithAI,
  fetchMailbox,
  formatDate,
  getConversations,
  getEmailThread,
  getUnreadCount,
  markConversationRead,
  sendChatEmail,
  type Conversation,
  type EmailMessage,
} from "@/app/hr/_lib/api";

const CONVERSATION_POLL_MS = 10000;
const THREAD_POLL_MS = 8000;

function TimeLabel({ iso }: { iso?: string | null }) {
  const [label, setLabel] = useState("");
  useEffect(() => {
    const compute = () => {
      if (!iso) {
        setLabel("");
        return;
      }
      const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
      if (seconds < 5) setLabel("now");
      else if (seconds < 60) setLabel(`${seconds}s`);
      else if (seconds < 3600) setLabel(`${Math.floor(seconds / 60)}m`);
      else if (seconds < 86400) setLabel(`${Math.floor(seconds / 3600)}h`);
      else setLabel(new Date(iso).toLocaleDateString());
    };
    const initial = window.setTimeout(compute, 0);
    const timer = setInterval(compute, 60000);
    return () => {
      window.clearTimeout(initial);
      clearInterval(timer);
    };
  }, [iso]);
  return <>{label}</>;
}

function Avatar({ name }: { name: string | null }) {
  const initials = (name ?? "?")
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center bg-navy-600 text-xs font-semibold text-white">
      {initials}
    </span>
  );
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [thread, setThread] = useState<EmailMessage[]>([]);
  const [chatText, setChatText] = useState("");
  const [busy, setBusy] = useState(false);
  const [aiDrafting, setAiDrafting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [totalUnread, setTotalUnread] = useState(0);
  const [view, setView] = useState<"list" | "thread">("list");
  const bottomRef = useRef<HTMLDivElement>(null);

  const selected =
    conversations.find((c) => c.application_id === selectedId) ?? null;

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  const refreshConvs = useCallback(async () => {
    try {
      const rows = await getConversations();
      setConversations((prev) => {
        const changed = JSON.stringify(rows) !== JSON.stringify(prev);
        if (changed) return rows;
        return prev;
      });
      setSelectedId((current) => {
        if (current) return current;
        const firstUnread = rows.find((r) => r.unread > 0);
        return (firstUnread ?? rows[0])?.application_id ?? null;
      });
    } catch {
      // keep the last known list on transient failures
    }
  }, []);

  const refreshUnread = useCallback(async () => {
    try {
      const { unread } = await getUnreadCount();
      setTotalUnread(unread);
    } catch {
      // transient
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => {
      void refreshUnread();
      void refreshConvs();
    }, 0);
    const timer = setInterval(() => {
      void refreshUnread();
      void refreshConvs();
    }, CONVERSATION_POLL_MS);
    return () => {
      window.clearTimeout(initial);
      clearInterval(timer);
    };
  }, [refreshConvs, refreshUnread]);

  const loadThread = useCallback(async (applicationId: string) => {
    try {
      setThread(await getEmailThread(applicationId));
    } catch {
      // transient
    }
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const timer = setInterval(() => void loadThread(selectedId), THREAD_POLL_MS);
    return () => clearInterval(timer);
  }, [selectedId, loadThread]);

  useEffect(() => {
    if (selectedId && bottomRef.current) {
      bottomRef.current.scrollIntoView({ block: "end" });
    }
  }, [thread, selectedId]);

  const openConversation = useCallback(
    async (applicationId: string) => {
      setSelectedId(applicationId);
      setView("thread");
      setThread([]);
      void loadThread(applicationId);
      try {
        await markConversationRead(applicationId);
        setConversations((prev) =>
          prev.map((c) =>
            c.application_id === applicationId ? { ...c, unread: 0 } : c
          )
        );
        setTotalUnread((prev) => Math.max(0, prev - (selected?.unread ?? 0)));
        void refreshUnread();
      } catch {
        // read marker is best-effort
      }
    },
    [loadThread, selected?.unread, refreshUnread]
  );

  async function checkInbox() {
    setBusy(true);
    setError(null);
    try {
      const result = await fetchMailbox();
      if (!result.enabled) {
        setError(
          "Inbox checking is turned off — enable IMAP_ENABLED in the backend settings."
        );
      } else {
        setNotice(
          result.processed.length > 0
            ? "Inbox checked — new messages pulled in."
            : "Inbox checked — no new messages."
        );
      }
      await refreshUnread();
      await refreshConvs();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Inbox check failed");
    } finally {
      setBusy(false);
    }
  }

  async function sendChatMessage() {
    if (!selectedId || !chatText.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const lastOutbound = [...thread]
        .reverse()
        .find((message) => message.direction === "OUTBOUND");
      let subject = lastOutbound?.subject ?? "Re: Application Update";
      if (!subject.toLowerCase().startsWith("re:")) subject = `Re: ${subject}`;
      await sendChatEmail(selectedId, {
        type: "REPLY",
        subject,
        body: chatText.trim(),
      });
      setChatText("");
      setNotice("Message sent and the candidate has been emailed.");
      await loadThread(selectedId);
      await refreshConvs();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Message could not be sent");
    } finally {
      setBusy(false);
    }
  }

  async function aiReplySuggestion() {
    if (!selectedId) return;
    const lastInbound = [...thread]
      .reverse()
      .find((message) => message.direction === "INBOUND");
    setAiDrafting(true);
    setError(null);
    try {
      const draft = await draftEmailWithAI(selectedId, {
        email_type: "REPLY",
        hr_notes: lastInbound
          ? `A candidate asked: ${lastInbound.subject}\n${lastInbound.body ?? ""}\n\nReply directly, answer their question, keep it short and warm.`
          : "Write a short, warm reply asking how we can help.",
      });
      setChatText(draft.body);
      setNotice("Draft ready — review and edit, then press Send.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Draft could not be generated");
    } finally {
      setAiDrafting(false);
    }
  }

  const listPane = (
    <div className="flex h-full flex-col overflow-hidden border-r border-zinc-200 bg-white">
      <div className="flex items-center justify-between gap-2 border-b border-zinc-200 px-4 py-3">
        <div>
          <h1 className="text-base font-semibold text-zinc-900">
            Chats
            {totalUnread > 0 ? (
              <span className="ml-2 rounded-full bg-navy-600 px-2 py-0.5 text-[11px] font-semibold text-white">
                {totalUnread} new
              </span>
            ) : null}
          </h1>
          <p className="text-xs text-zinc-500">
            Candidate messages arrive here by email.
          </p>
        </div>
        <Button variant="secondary" onClick={() => void checkInbox()} disabled={busy}>
          {busy ? "Checking…" : "Check inbox"}
        </Button>
      </div>

      {conversations.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-6">
          <EmptyState title="No conversations yet">
            <p className="text-xs text-zinc-500">
              Email a candidate to start a thread — replies land here.
            </p>
          </EmptyState>
        </div>
      ) : (
        <ul className="min-h-0 flex-1 divide-y divide-zinc-100 overflow-y-auto">
          {conversations.map((conversation) => {
            const active = conversation.application_id === selectedId;
            return (
              <li key={conversation.application_id}>
                <button
                  type="button"
                  onClick={() => void openConversation(conversation.application_id)}
                  className={`flex w-full items-start gap-3 px-4 py-3 text-left transition ${
                    active ? "bg-navy-50" : "hover:bg-zinc-50"
                  }`}
                >
                  <Avatar name={conversation.candidate_name} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="truncate text-sm font-semibold text-zinc-900">
                        {conversation.candidate_name ?? conversation.candidate_email ?? "Candidate"}
                      </p>
                      <span className="shrink-0 text-[11px] text-zinc-400">
                        <TimeLabel iso={conversation.updated_at} />
                      </span>
                    </div>
                    <p className="truncate text-xs text-zinc-500">
                      {conversation.job_title ?? "Application"}
                    </p>
                    <p className="truncate text-[13px] text-zinc-600">
                      {conversation.last_message?.direction === "INBOUND" ? "" : "You: "}
                      {conversation.last_message?.subject ?? ""}
                      {conversation.last_message?.body
                        ? ` — ${conversation.last_message.body}`
                        : ""}
                    </p>
                  </div>
                  {conversation.unread > 0 ? (
                    <span className="mt-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-navy-600 px-1.5 text-[11px] font-semibold text-white">
                      {conversation.unread}
                    </span>
                  ) : null}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );

  const threadPane = selected ? (
    <div className="flex h-full flex-col bg-white">
      <div className="flex items-start justify-between gap-3 border-b border-zinc-200 px-5 py-3">
        <div>
          <h2 className="text-base font-semibold text-zinc-900">
            {selected.candidate_name ?? selected.candidate_email ?? "Candidate"}
          </h2>
          <p className="text-xs text-zinc-500">
            {selected.job_title ?? "Application"}
            {selected.candidate_email ? ` · ${selected.candidate_email}` : ""}
          </p>
        </div>
        {selected.candidate_id ? (
          <Link
            href={`/dashboard/candidates/${selected.application_id}`}
            className="flex h-8 w-8 items-center justify-center text-zinc-400 transition hover:bg-zinc-100 hover:text-navy-700"
            title="Open application"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
          </Link>
        ) : null}
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto bg-zinc-50 p-4">
        {thread.length === 0 ? (
          <div className="m-auto max-w-sm text-center">
            <p className="text-sm font-medium text-zinc-700">No messages yet</p>
            <p className="text-xs text-zinc-500">
              Send the first message below — the candidate receives it by email
              and their reply shows up here.
            </p>
          </div>
        ) : (
          <>
            {thread.map((message) => {
              const fromCandidate = message.direction === "INBOUND";
              return (
                <div key={message.id} className="flex flex-col gap-1">
                  <div
                    className={`max-w-[85%] whitespace-pre-wrap border px-4 py-3 text-sm shadow-sm ${
                      fromCandidate
                        ? "self-start border-zinc-200 bg-white text-zinc-900"
                        : "self-end border-navy-700 bg-navy-700 text-white"
                    }`}
                  >
                    <p
                      className={`mb-0.5 text-[11px] font-semibold uppercase tracking-wide ${
                        fromCandidate ? "text-zinc-400" : "text-navy-200"
                      }`}
                    >
                      {fromCandidate
                        ? selected.candidate_name ?? "Candidate"
                        : "You (HR)"}
                    </p>
                    <p className="text-xs text-zinc-400">{message.subject}</p>
                    <p className="mt-1">{message.body ?? "(no text)"}</p>
                  </div>
                  <p
                    className={`text-[11px] text-zinc-400 ${
                      fromCandidate ? "self-start pl-1" : "self-end pr-1"
                    }`}
                  >
                    {message.created_at ? formatDate(message.created_at) : ""}
                    {message.status === "FAILED" ? " · delivery failed" : ""}
                  </p>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      <div className="border-t border-zinc-200 p-3">
        <textarea
          rows={3}
          value={chatText}
          onChange={(event) => setChatText(event.target.value)}
          placeholder="Write a message for the candidate…"
          className={inputClass()}
        />
        <div className="mt-2 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={aiReplySuggestion}
            disabled={aiDrafting || busy}
            className="text-sm font-medium text-navy-600 hover:underline disabled:opacity-50"
          >
            {aiDrafting ? "Drafting…" : "Draft reply"}
          </button>
          <Button
            variant="primary"
            onClick={() => void sendChatMessage()}
            disabled={busy || !chatText.trim()}
          >
            {busy ? "Sending…" : "Send"}
          </Button>
        </div>
      </div>
    </div>
  ) : (
    <div className="flex h-full items-center justify-center bg-white p-6">
      <EmptyState title="Select a conversation">
        <p className="text-xs text-zinc-500">Pick a chat from the list to view it.</p>
      </EmptyState>
    </div>
  );

  return (
    <main className="mx-auto w-full max-w-7xl p-4 sm:p-6">
      {error ? (
        <div className="mb-4 border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="mb-4 border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {notice}
        </div>
      ) : null}

      <div className="h-[calc(100dvh-16rem)] overflow-hidden border border-zinc-200 shadow-sm md:h-[calc(100dvh-12rem)] lg:h-[calc(100dvh-10rem)]">
        {/* Desktop: two panes side by side */}
        <div className="hidden h-full md:grid md:grid-cols-[23rem_minmax(0,1fr)] md:grid-rows-[minmax(0,1fr)]">
          {listPane}
          {threadPane}
        </div>

        {/* Mobile: switch between list and thread */}
        <div className="flex h-full flex-col md:hidden">
          <div className="flex shrink-0 border-b border-zinc-200 text-sm font-medium">
            <button
              type="button"
              onClick={() => setView("list")}
              className={`flex-1 px-4 py-2 ${
                view === "list"
                  ? "border-b-2 border-navy-600 text-navy-700"
                  : "text-zinc-500"
              }`}
            >
              Chats
              {totalUnread > 0 ? ` (${totalUnread})` : ""}
            </button>
            <button
              type="button"
              onClick={() => {
                if (selectedId) setView("thread");
              }}
              className={`flex-1 px-4 py-2 ${
                view === "thread"
                  ? "border-b-2 border-navy-600 text-navy-700"
                  : "text-zinc-500"
              }`}
            >
              Thread
            </button>
          </div>
          <div className="min-h-0 flex-1">{view === "list" ? listPane : threadPane}</div>
        </div>
      </div>
    </main>
  );
}