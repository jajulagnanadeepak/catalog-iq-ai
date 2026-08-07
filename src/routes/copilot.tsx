import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/copilot")({
  component: CopilotPage,
});

function CopilotPage() {
  return null;
}
