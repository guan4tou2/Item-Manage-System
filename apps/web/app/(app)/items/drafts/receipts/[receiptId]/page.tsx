import { ReceiptDetail } from "@/components/ai/receipt-detail"

export default async function ReceiptPage({ params }: {
  params: Promise<{ receiptId: string }>
}) {
  const { receiptId } = await params
  return <ReceiptDetail receiptId={receiptId} />
}
