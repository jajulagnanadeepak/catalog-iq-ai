import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Bot, Send, User } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProductCard } from "@/components/catalog/product-card";
import { postCopilot } from "@/lib/api/services";
import type { CopilotMessage, Product } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/copilot")({
  head: () => ({
    meta: [
      { title: "AI Shopping Copilot — CatalogIQ AI" },
      {
        name: "description",
        content:
          "Chat with the CatalogIQ copilot to compare products, narrow options and get explained recommendations.",
      },
      { property: "og:title", content: "AI Shopping Copilot — CatalogIQ AI" },
      { property: "og:description", content: "A conversational assistant for your catalog." },
    ],
  }),
  component: CopilotPage,
});

const STARTERS = [
  "I need a jacket for a rainy city commute",
  "Compare your two best-rated sneakers",
  "Build a capsule wardrobe under $600",
];

function CopilotPage() {
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      role: "assistant",
      content:
        "Hi — I'm your catalog copilot. Tell me what you're shopping for, the occasion, and any budget, and I'll narrow it down with reasoning you can check.",
    },
  ]);
  const [suggestions, setSuggestions] = useState<Product[]>([]);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const send = useMutation({
    mutationFn: (next: CopilotMessage[]) => postCopilot({ messages: next }),
    onSuccess: (reply) => {
      setMessages((m) => [...m, reply.message]);
      setSuggestions(reply.suggestions);
    },
  });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, send.isPending]);

  function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || send.isPending) return;
    const next: CopilotMessage[] = [...messages, { role: "user", content: trimmed }];
    setMessages(next);
    setInput("");
    send.mutate(next);
  }

  return (
    <AppShell title="AI Shopping Copilot" description="Conversational discovery with explanations">
      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <Card className="flex h-[70vh] flex-col gap-0 overflow-hidden p-0 shadow-card">
          <div className="flex-1 space-y-6 overflow-y-auto p-6">
            {messages.map((m, i) => (
              <div key={i} className={cn("flex gap-3", m.role === "user" && "justify-end")}>
                {m.role === "assistant" && (
                  <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                    <Bot className="size-4" />
                  </span>
                )}
                <div
                  className={cn(
                    "max-w-[85%] text-sm leading-relaxed",
                    m.role === "user"
                      ? "rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-primary-foreground"
                      : "text-foreground",
                  )}
                >
                  {m.content}
                </div>
                {m.role === "user" && (
                  <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
                    <User className="size-4" />
                  </span>
                )}
              </div>
            ))}

            {send.isPending && (
              <div className="flex gap-3">
                <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                  <Bot className="size-4" />
                </span>
                <p className="animate-pulse text-sm text-muted-foreground">Thinking…</p>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="border-t border-border p-4">
            <div className="mb-3 flex flex-wrap gap-2">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => submit(s)}
                  className="rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
            <form
              className="flex items-center gap-2"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                submit(input);
              }}
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask the copilot anything about the catalog…"
              />
              <Button type="submit" size="icon" disabled={send.isPending} aria-label="Send">
                <Send className="size-4" />
              </Button>
            </form>
          </div>
        </Card>

        <div>
          <h2 className="mb-4 text-base font-semibold">Copilot picks</h2>
          {suggestions.length === 0 ? (
            <Card className="items-center gap-2 p-10 text-center">
              <p className="text-sm text-muted-foreground">
                Product suggestions from the conversation will appear here.
              </p>
            </Card>
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-1">
              {suggestions.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
