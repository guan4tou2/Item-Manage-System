import { FloorPlan } from "@/components/locations/floor-plan"

export default async function FloorPlanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <FloorPlan locationId={Number(id)} />
}
