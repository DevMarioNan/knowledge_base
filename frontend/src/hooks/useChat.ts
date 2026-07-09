import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api";
import { env } from "@/lib/env";

export interface CitationData {
  citation_index: number;
  chunk_id: string;
  document_id: string;
  content_excerpt: string | null;
  page_number: number | null;
  relevance_score: number | null;
}

export interface ChatMessageData {
  id: string;
  thread_id: string;
  role: "user" | "assistant";
  content: string;
  grounding_failure: boolean;
  citations: CitationData[];
  created_at: string;
}

export interface ThreadData {
  id: string;
  title: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

interface SSEEvent {
  type: "token" | "citations" | "done" | "grounding_failure" | "error" | "thread";
  content?: string;
  citations?: CitationData[];
  message_id?: string;
  message?: string;
  thread_id?: string;
  title?: string;
}

export function useChat(trialId: string) {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [threads, setThreads] = useState<ThreadData[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [groundingFailure, setGroundingFailure] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const token = () => localStorage.getItem("access_token");

  const fetchThreads = useCallback(async () => {
    try {
      const res = await fetch(`${env.apiBaseUrl}/api/trials/${trialId}/threads`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!res.ok) return;
      const data: ThreadData[] = await res.json();
      setThreads(data);
    } catch {
      // ignore
    }
  }, [trialId]);

  const loadThreadMessages = useCallback(async (threadId: string) => {
    try {
      const res = await fetch(`${env.apiBaseUrl}/api/threads/${threadId}/messages`, {
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!res.ok) return;
      const data: ChatMessageData[] = await res.json();
      setMessages(data);
      setActiveThreadId(threadId);
      setGroundingFailure(false);
      setError(null);
    } catch {
      // ignore
    }
  }, []);

  const createThread = useCallback(async (): Promise<null> => {
    setActiveThreadId(null);
    setMessages([]);
    setGroundingFailure(false);
    setError(null);
    return null;
  }, []);

  const sendMessage = useCallback(
    async (query: string, threadId?: string | null) => {
      if (!query.trim() || isStreaming) return;

      setIsStreaming(true);
      setGroundingFailure(false);
      setError(null);

      const userMessage: ChatMessageData = {
        id: `temp-${Date.now()}`,
        thread_id: threadId || activeThreadId || "",
        role: "user",
        content: query,
        grounding_failure: false,
        citations: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      const assistantMessage: ChatMessageData = {
        id: `temp-assistant-${Date.now()}`,
        thread_id: threadId || activeThreadId || "",
        role: "assistant",
        content: "",
        grounding_failure: false,
        citations: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      abortRef.current = new AbortController();

      try {
        const res = await fetch(
          `${env.apiBaseUrl}/api/trials/${trialId}/chat`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token()}`,
            },
            body: JSON.stringify({
              thread_id: threadId || activeThreadId || null,
              query,
            }),
            signal: abortRef.current.signal,
          }
        );

        if (!res.ok) {
          const errBody = await res.text();
          setError(`Chat failed: ${res.status} ${errBody}`);
          setIsStreaming(false);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          setError("No response body");
          setIsStreaming(false);
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();
            if (!data) continue;

            try {
              const event: SSEEvent = JSON.parse(data);
              handleSSEEvent(event);
            } catch {
              // skip malformed events
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [trialId, activeThreadId, isStreaming]
  );

  function handleSSEEvent(event: SSEEvent) {
    switch (event.type) {
      case "token":
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === "assistant") {
            updated[updated.length - 1] = { ...last, content: last.content + (event.content || "") };
          }
          return updated;
        });
        break;

      case "citations":
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === "assistant" && event.citations) {
            updated[updated.length - 1] = { ...last, citations: event.citations };
          }
          return updated;
        });
        break;

      case "done":
        if (event.message_id) {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = { ...last, id: event.message_id! };
            }
            return updated;
          });
        }
        fetchThreads();
        break;

      case "grounding_failure":
        setGroundingFailure(true);
        break;

      case "thread":
        if (event.thread_id) {
          setActiveThreadId(event.thread_id);
          fetchThreads();
        }
        break;

      case "error":
        setError(event.message || "An error occurred");
        break;
    }
  }

  const deleteThread = useCallback(async (threadId: string) => {
    await api.delete(`/api/threads/${threadId}`);
    setThreads((prev) => prev.filter((t) => t.id !== threadId));
    if (activeThreadId === threadId) {
      setActiveThreadId(null);
      setMessages([]);
    }
  }, [activeThreadId]);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  return {
    messages,
    isStreaming,
    threads,
    activeThreadId,
    setActiveThreadId: loadThreadMessages,
    fetchThreads,
    sendMessage,
    createThread,
    loadThreadMessages,
    error,
    groundingFailure,
    deleteThread,
    stopStreaming,
  };
}
