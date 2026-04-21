import { LoginForm } from '@/features/auth/login-form'

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-12">
      <h1 className="text-2xl font-bold">登入</h1>
      <LoginForm />
    </main>
  )
}
