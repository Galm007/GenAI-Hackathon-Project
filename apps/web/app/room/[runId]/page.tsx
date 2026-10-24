import { WarRoom } from "@/components/room/WarRoom";

export default async function Page({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <WarRoom source={{ kind: "live", runId }} />;
}
