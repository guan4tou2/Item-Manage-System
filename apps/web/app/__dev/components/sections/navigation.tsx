"use client"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { Section } from "../section"

export function NavigationSection() {
  return (
    <Section title="Navigation" description="導航類元件。">
      <Tabs defaultValue="a" className="w-full max-w-md">
        <TabsList>
          <TabsTrigger value="a">概覽</TabsTrigger>
          <TabsTrigger value="b">詳情</TabsTrigger>
          <TabsTrigger value="c">紀錄</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Tab A 內容</TabsContent>
        <TabsContent value="b">Tab B 內容</TabsContent>
        <TabsContent value="c">Tab C 內容</TabsContent>
      </Tabs>

      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="#">首頁</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink href="#">物品</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>詳情</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <Pagination>
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious href="#" />
          </PaginationItem>
          <PaginationItem>
            <PaginationLink href="#" isActive>
              1
            </PaginationLink>
          </PaginationItem>
          <PaginationItem>
            <PaginationLink href="#">2</PaginationLink>
          </PaginationItem>
          <PaginationItem>
            <PaginationEllipsis />
          </PaginationItem>
          <PaginationItem>
            <PaginationNext href="#" />
          </PaginationItem>
        </PaginationContent>
      </Pagination>

      <div className="w-full max-w-sm rounded-md border">
        <Command>
          <CommandInput placeholder="搜尋…" />
          <CommandList>
            <CommandEmpty>無結果。</CommandEmpty>
            <CommandGroup heading="建議">
              <CommandItem>新增物品</CommandItem>
              <CommandItem>查詢歷史</CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </div>
    </Section>
  )
}
