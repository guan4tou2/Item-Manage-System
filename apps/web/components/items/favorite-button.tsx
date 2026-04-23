"use client"
import { Star } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useToggleFavorite } from "@/lib/hooks/use-favorite"

interface Props {
  itemId: string
  isFavorite: boolean
}

export function FavoriteButton({ itemId, isFavorite }: Props) {
  const toggle = useToggleFavorite()
  return (
    <Button
      size="icon"
      variant="ghost"
      aria-label={isFavorite ? "unfavorite" : "favorite"}
      onClick={() => toggle.mutate(itemId)}
      disabled={toggle.isPending}
    >
      <Star className={cn("h-4 w-4", isFavorite && "fill-amber-400 text-amber-400")} />
    </Button>
  )
}
