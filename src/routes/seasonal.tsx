import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/seasonal")({
  component: SeasonalPage,
});

function SeasonalPage() {
  return null;
}
