'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api/client'
import { useLogin } from '@/lib/auth/use-auth'

export function LoginForm() {
  const router = useRouter()
  const login = useLogin()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    try {
      await login.mutateAsync({ username, password })
      router.push('/')
    } catch (err) {
      if (err instanceof ApiError) {
        setError('帳號或密碼錯誤')
      } else {
        setError('登入失敗，請稍後再試')
      }
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto flex w-full max-w-sm flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="username" className="text-sm font-medium">
          使用者名稱
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          required
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="password" className="text-sm font-medium">
          密碼
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Button type="submit" disabled={login.isPending}>
        {login.isPending ? '登入中…' : '登入'}
      </Button>
    </form>
  )
}
