export default async function DemoRoomPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;

  return (
    <div className="flex h-screen flex-col bg-[var(--color-room)]">
      <header className="flex h-14 items-center justify-between border-b border-[var(--color-line)] px-4">
        <div className="flex items-center gap-3">
          <span className="font-display font-semibold text-[var(--color-ink)]">
            ADCOM ▸ Demo Replay
          </span>
          <span className="rounded bg-[var(--color-panel-2)] px-2 py-0.5 font-mono text-xs text-[var(--color-muted)]">
            {name}
          </span>
        </div>
      </header>
      <main className="flex-1 p-6">
        <p className="text-[var(--color-muted)]">
          Demo replay for persona <code className="text-[var(--color-ink)]">{name}</code>.
        </p>
      </main>
    </div>
  );
}
