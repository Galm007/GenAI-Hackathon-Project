import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { connectStream, POLL_MS, pollUrlFor, replaySpeed, STALL_MS } from "./stream";
import { useRunStore } from "../store/run-store";

class FakeEventSource {
  static last: FakeEventSource;
  closed = false;
  listeners: Record<string, (e: MessageEvent<string>) => void> = {};
  constructor(public url: string) {
    FakeEventSource.last = this;
  }
  addEventListener(type: string, fn: (e: MessageEvent<string>) => void) {
    this.listeners[type] = fn;
  }
  close() {
    this.closed = true;
  }
  emit(env: { seq: number; event: string; [k: string]: unknown }) {
    this.listeners[env.event]?.({ data: JSON.stringify(env) } as MessageEvent<string>);
  }
}

const env = (seq: number, event: string, extra: object = {}) => ({ seq, run_id: "r", ts: seq, event, ...extra });

describe("pollUrlFor", () => {
  it("maps a live run's stream url to its events url", () => {
    expect(pollUrlFor("/api/evaluate/abc-1/stream")).toBe("/api/evaluate/abc-1/events");
    expect(pollUrlFor("https://x.test/api/evaluate/abc/stream?after=3")).toBe("https://x.test/api/evaluate/abc/events");
  });
  it("leaves demo replays alone", () => {
    expect(pollUrlFor("/api/demo/maya-uiuc/stream")).toBeNull();
  });
});

describe("replaySpeed", () => {
  it("reads and clamps the speed query", () => {
    expect(replaySpeed("?speed=4")).toBe(4);
    expect(replaySpeed("?projector=1&speed=2.5")).toBe(2.5);
    expect(replaySpeed("?speed=100")).toBe(8);
    expect(replaySpeed("?speed=0.01")).toBe(0.25);
  });
  it("ignores missing or invalid values", () => {
    expect(replaySpeed("")).toBeNull();
    expect(replaySpeed("?speed=fast")).toBeNull();
    expect(replaySpeed("?speed=-2")).toBeNull();
  });
});

describe("connectStream polling fallback", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("window", {});
    vi.stubGlobal("EventSource", FakeEventSource);
    vi.stubGlobal("requestAnimationFrame", (fn: () => void) => setTimeout(fn, 0) as unknown as number);
    vi.stubGlobal("cancelAnimationFrame", (id: number) => clearTimeout(id));
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    useRunStore.setState({ runs: {} });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const status = (id: string) => useRunStore.getState().runs[id]?.status;

  it("does not poll while the stream is delivering", async () => {
    const stop = connectStream("live-ok", "/api/evaluate/live-ok/stream");
    for (let i = 0; i < 4; i++) {
      FakeEventSource.last.emit(env(i, "progress", { node: "n", message: "m" }));
      await vi.advanceTimersByTimeAsync(POLL_MS);
    }
    expect(fetchMock).not.toHaveBeenCalled();
    stop();
  });

  it("reads events from the JSON endpoint when the stream is buffered, and ignores the late flush", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ events: [env(0, "run_started", { school_slug: "uiuc" }), env(1, "progress", { node: "n", message: "m" })], done: false }),
    });
    fetchMock.mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ events: [env(2, "done", { status: "complete" })], done: true }),
    });

    connectStream("live-buffered", "/api/evaluate/live-buffered/stream");
    await vi.advanceTimersByTimeAsync(STALL_MS + POLL_MS);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/evaluate/live-buffered/events?after=-1");
    expect(status("live-buffered")).toBe("running");

    await vi.advanceTimersByTimeAsync(POLL_MS);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/evaluate/live-buffered/events?after=1");
    expect(status("live-buffered")).toBe("complete");

    const es = FakeEventSource.last;
    expect(es.closed).toBe(true);
    await vi.advanceTimersByTimeAsync(POLL_MS * 3);
    expect(fetchMock).toHaveBeenCalledTimes(2);       // polling stopped at done
  });

  it("never polls a demo replay", async () => {
    connectStream("demo-maya", "/api/demo/maya/stream");
    await vi.advanceTimersByTimeAsync(STALL_MS * 3);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
