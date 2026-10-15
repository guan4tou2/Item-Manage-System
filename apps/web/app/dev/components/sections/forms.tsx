"use client"

import { useState } from "react"

import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"

import { Section } from "../section"

export function FormsSection() {
  const [slider, setSlider] = useState([50])
  return (
    <Section title="Forms" description="輸入類元件。所有元件皆以鍵盤與讀屏友善為目標。">
      <div className="flex w-full max-w-sm flex-col gap-2">
        <Label htmlFor="demo-input">Input</Label>
        <Input id="demo-input" placeholder="物品名稱" />
      </div>
      <div className="flex w-full max-w-sm flex-col gap-2">
        <Label htmlFor="demo-textarea">Textarea</Label>
        <Textarea id="demo-textarea" placeholder="備註" />
      </div>
      <div className="flex w-full max-w-sm flex-col gap-2">
        <Label htmlFor="demo-select">Select</Label>
        <Select>
          <SelectTrigger id="demo-select">
            <SelectValue placeholder="選擇位置" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="bedroom">臥室</SelectItem>
            <SelectItem value="kitchen">廚房</SelectItem>
            <SelectItem value="office">書房</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center gap-3">
        <Checkbox id="demo-check" />
        <Label htmlFor="demo-check">已整理</Label>
      </div>
      <RadioGroup defaultValue="a" className="flex gap-4">
        <div className="flex items-center gap-2">
          <RadioGroupItem value="a" id="r1" />
          <Label htmlFor="r1">選項 A</Label>
        </div>
        <div className="flex items-center gap-2">
          <RadioGroupItem value="b" id="r2" />
          <Label htmlFor="r2">選項 B</Label>
        </div>
      </RadioGroup>
      <div className="flex items-center gap-3">
        <Switch id="demo-switch" />
        <Label htmlFor="demo-switch">開啟通知</Label>
      </div>
      <div className="w-64 space-y-2">
        <Label>Slider — {slider[0]}</Label>
        <Slider value={slider} onValueChange={setSlider} max={100} />
      </div>
    </Section>
  )
}
