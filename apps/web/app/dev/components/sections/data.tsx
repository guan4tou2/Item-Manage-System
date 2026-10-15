"use client"

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import { Section } from "../section"

export function DataSection() {
  return (
    <Section title="Data Display" description="資料呈現類元件。">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Card 標題</CardTitle>
          <CardDescription>一個完整 Card 結構。</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm">這裡放內容。</p>
        </CardContent>
      </Card>

      <Table className="max-w-md">
        <TableHeader>
          <TableRow>
            <TableHead>名稱</TableHead>
            <TableHead>位置</TableHead>
            <TableHead className="text-right">數量</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>相機</TableCell>
            <TableCell>書房</TableCell>
            <TableCell className="text-right">1</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>筆記本</TableCell>
            <TableCell>抽屜</TableCell>
            <TableCell className="text-right">3</TableCell>
          </TableRow>
        </TableBody>
      </Table>

      <div className="flex items-center gap-3">
        <Avatar>
          <AvatarImage src="" alt="" />
          <AvatarFallback>IM</AvatarFallback>
        </Avatar>
        <div>
          <div className="text-sm font-medium">User</div>
          <div className="text-xs text-muted-foreground">email@example.com</div>
        </div>
      </div>

      <div className="w-48">
        <div className="text-sm">左</div>
        <Separator className="my-2" />
        <div className="text-sm">右</div>
      </div>

      <Accordion type="single" collapsible className="w-full max-w-md">
        <AccordionItem value="a">
          <AccordionTrigger>什麼是 shadcn/ui？</AccordionTrigger>
          <AccordionContent>
            一組可複製貼上的 React 元件，構建於 Radix primitives 之上。
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="b">
          <AccordionTrigger>為什麼要深色模式？</AccordionTrigger>
          <AccordionContent>
            降低視覺疲勞、配合 OLED 省電、尊重使用者偏好。
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <ScrollArea className="h-32 w-48 rounded-md border p-3 text-sm">
        {Array.from({ length: 20 }).map((_, i) => (
          <div key={i}>項目 {i + 1}</div>
        ))}
      </ScrollArea>
    </Section>
  )
}
