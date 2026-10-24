"use client";

import { useEffect } from "react";
import { Play, RotateCcw } from "lucide-react";
import type { RunSource } from "@/lib/stream";

export function ReplayControls({ source }: { source: RunSource }) {
  const replay = () => {
    const projector = new URLSearchParams(window.location.search).get("projector") === "1";
    // A fresh navigation resets sequence state so replaying a completed demo works again.
    window.location.assign(`/room/demo/maya-uiuc${projector ? "?projector=1" : ""}`);
  };
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (!event.shiftKey || event.ctrlKey || event.metaKey || event.altKey || event.key.toLowerCase() !== "r") return;
      if ((event.target as HTMLElement)?.closest("input, textarea, select, [contenteditable=true]")) return;
      event.preventDefault();
      replay();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  const demo = source.kind === "demo";
  return <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-line bg-panel px-4 py-2 text-[11px] sm:px-6">
    <p className="leading-relaxed text-muted">{demo ? <><span className="mr-2 rounded border border-waitlist/30 bg-waitlist/5 px-2 py-0.5 font-mono uppercase tracking-wider text-waitlist">Fictional replay</span>Sample applicants and figures. No live admissions data.</> : "Your committee room"}</p>
    <button type="button" onClick={replay} className="inline-flex items-center gap-1.5 rounded px-1 py-0.5 text-advocate hover:underline">
      {demo ? <RotateCcw className="size-3" /> : <Play className="size-3" />}{demo ? "Restart replay" : "Switch to demo"}<kbd className="ml-2 hidden rounded border border-line px-1.5 font-mono text-[9px] text-muted sm:inline">Shift R</kbd>
    </button>
  </div>;
}
