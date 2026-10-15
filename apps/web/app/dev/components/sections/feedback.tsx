"use client"

import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"

import { Section } from "../section"

export function FeedbackSection() {
  return (
    <Section title="Feedback" description="狀態與訊息類元件。">
      <Alert className="max-w-md">
        <AlertTitle>資訊</AlertTitle>
        <AlertDescription>這是一個 Alert 的示範內容。</AlertDescription>
      </Alert>

      <div className="flex flex-wrap gap-2">
        <Badge>預設</Badge>
        <Badge variant="secondary">次要</Badge>
        <Badge variant="destructive">錯誤</Badge>
        <Badge variant="outline">外框</Badge>
      </div>

      <div className="space-y-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-40" />
      </div>

      <div className="w-64 space-y-2">
        <Progress value={62} />
        <p className="text-xs text-muted-foreground">62% 完成</p>
      </div>

      <Button
        onClick={() =>
          toast.success("已儲存", { description: "偏好設定已同步。" })
        }
      >
        觸發 Toast
      </Button>
    </Section>
  )
}
