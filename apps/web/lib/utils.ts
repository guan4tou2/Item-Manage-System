import { clsx, type ClassValue } from 'clsx'
import { extendTailwindMerge } from 'tailwind-merge'

// 套件維持 v2；補上此次遷移使用的 v4 類別，讓呼叫端的覆寫仍然有效。
const isVariableShorthand = (value: string) => /^\(--[^)]+\)$/.test(value)
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      'outline-style': [{ outline: ['hidden'] }],
      'transform-origin': [{ origin: [isVariableShorthand] }],
      'max-h': [{ 'max-h': [isVariableShorthand] }],
    },
  },
})

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
