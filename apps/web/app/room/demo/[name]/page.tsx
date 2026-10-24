import { WarRoom } from "@/components/room/WarRoom";

export default async function DemoPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  return <WarRoom source={{ kind: "demo", name }} />;
}
