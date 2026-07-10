import { useEffect, useRef, useState } from "react";
import { useChat } from "@/hooks/useChat";
import MessageBubble from "./MessageBubble";
import SourcePanel from "./SourcePanel";
import GroundingFailure from "./GroundingFailure";
import ThreadList from "./ThreadList";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Square, PanelRightOpen, PanelRightClose } from "lucide-react";

interface ChatPanelProps {
  trialId: string;
}

export default function ChatPanel({ trialId }: ChatPanelProps) {
  const {
    messages,
    isStreaming,
    threads,
    activeThreadId,
    sendMessage,
    setActiveThreadId,
    createThread,
    fetchThreads,
    error,
    groundingFailure,
    deleteThread,
    stopStreaming,
  } = useChat(trialId);

  const [input, setInput] = useState("");
  const [showSources, setShowSources] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  useEffect(() => {
    if (viewportRef.current) {
      viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    const query = input.trim();
    if (!query || isStreaming) return;
    setInput("");
    sendMessage(query, activeThreadId);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = async () => {
    await createThread();
    setShowSources(false);
    inputRef.current?.focus();
  };

  const lastAssistantMessage = [...messages]
    .reverse()
    .find((m) => m.role === "assistant");

  return (
    <div className="flex h-full border rounded-lg overflow-hidden">
      <ThreadList
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={setActiveThreadId}
        onCreateThread={handleNewChat}
        onDeleteThread={deleteThread}
      />

      <div className="flex-1 flex flex-col">
        <ScrollArea ref={scrollRef} viewportRef={viewportRef} className="flex-1 p-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center py-16">
              <h2 className="text-lg font-semibold mb-2">Ask a Question</h2>
              <p className="text-sm text-muted-foreground max-w-md">
                Ask a question about the documents in this trial. The system
                will search the documents and provide answers with citations.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role}
              content={msg.content}
              citations={msg.citations}
              grounding_failure={msg.grounding_failure}
            />
          ))}

          {groundingFailure && <GroundingFailure onRetry={() => inputRef.current?.focus()} />}

          {error && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3 text-sm text-destructive">
              {error}
            </div>
          )}
        </ScrollArea>

        <div className="border-t p-4">
          <div className="flex items-end gap-2">
            {lastAssistantMessage && lastAssistantMessage.citations.length > 0 && (
              <button
                onClick={() => setShowSources(!showSources)}
                className="p-2 rounded-md hover:bg-muted text-muted-foreground"
                title="Toggle sources panel"
              >
                {showSources ? (
                  <PanelRightClose className="h-4 w-4" />
                ) : (
                  <PanelRightOpen className="h-4 w-4" />
                )}
              </button>
            )}
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about the documents..."
                className="w-full resize-none rounded-md border bg-background px-3 py-2 text-sm pr-10 min-h-[40px] max-h-[120px]"
                rows={1}
                disabled={isStreaming}
              />
            </div>
            {isStreaming ? (
              <button
                onClick={stopStreaming}
                className="p-2 rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90"
                title="Stop generating"
              >
                <Square className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!input.trim()}
                className="p-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Send"
              >
                <Send className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {showSources && lastAssistantMessage && (
        <SourcePanel
          citations={lastAssistantMessage.citations}
          onClose={() => setShowSources(false)}
        />
      )}
    </div>
  );
}
