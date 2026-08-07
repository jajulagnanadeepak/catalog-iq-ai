import { useState, type FormEvent } from "react";
import { Search, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function SearchBar({
  defaultValue = "",
  placeholder = "Describe what you're looking for…",
  onSearch,
  suggestions = [],
  loading,
  className,
}: {
  defaultValue?: string;
  placeholder?: string;
  onSearch: (value: string) => void;
  suggestions?: string[];
  loading?: boolean;
  className?: string;
}) {
  const [value, setValue] = useState(defaultValue);

  function submit(e: FormEvent) {
    e.preventDefault();
    onSearch(value.trim());
  }

  return (
    <div className={cn("w-full", className)}>
      <form
        onSubmit={submit}
        className="flex items-center gap-2 rounded-xl border border-border bg-card p-2 shadow-card focus-within:ring-2 focus-within:ring-ring/40"
      >
        <Search className="ml-2 size-4 shrink-0 text-muted-foreground" />
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          className="border-0 bg-transparent shadow-none focus-visible:ring-0"
        />
        <Button type="submit" disabled={loading} className="shrink-0">
          <Sparkles className="size-4" />
          <span className="hidden sm:inline">{loading ? "Thinking…" : "Search"}</span>
        </Button>
      </form>

      {suggestions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setValue(s);
                onSearch(s);
              }}
              className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
