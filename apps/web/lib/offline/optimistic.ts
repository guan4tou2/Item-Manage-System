import type { CategoryTreeNode } from "@/lib/api/categories"
import type { LocationRead } from "@/lib/api/locations"
import type { ItemRead } from "@/lib/api/items"
import type { ItemFormValues } from "@/components/items/item-form"
import { updateBody } from "./steps"

export function optimisticItem(item: ItemRead, values: ItemFormValues, categories: CategoryTreeNode[] = [], locations: LocationRead[] = []): ItemRead {
  const flatten = (nodes: CategoryTreeNode[]): CategoryTreeNode[] => nodes.flatMap((node) => [node, ...flatten(node.children ?? [])])
  return {
    ...item, ...updateBody(values, item.track_batches),
    category: item.category?.id === values.category_id ? item.category : flatten(categories).find((category) => category.id === values.category_id) ?? null,
    location: item.location?.id === values.location_id ? item.location : locations.find((location) => location.id === values.location_id) ?? null,
    tags: values.tag_names.map((name, index) => item.tags.find((tag) => tag.name === name) ?? { id: -(index + 1), name }),
  } as ItemRead
}
