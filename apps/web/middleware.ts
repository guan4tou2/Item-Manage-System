import { NextResponse, type NextRequest } from "next/server"

const PROTECTED_PREFIXES = ["/dashboard", "/items", "/lists", "/settings"]
const AUTH_ONLY_PATHS = ["/login"]
const COOKIE_NAME = "ims_token"

function hasToken(req: NextRequest): boolean {
  const value = req.cookies.get(COOKIE_NAME)?.value
  return Boolean(value)
}

function isProtected(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix))
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  const loggedIn = hasToken(req)

  // Protected paths: not logged in → /login
  if (isProtected(pathname) && !loggedIn) {
    const url = req.nextUrl.clone()
    url.pathname = "/login"
    return NextResponse.redirect(url)
  }

  // Landing: logged in → /dashboard
  if (pathname === "/" && loggedIn) {
    const url = req.nextUrl.clone()
    url.pathname = "/dashboard"
    return NextResponse.redirect(url)
  }

  // Logged-in user hitting /login → /dashboard (UX polish)
  if (AUTH_ONLY_PATHS.includes(pathname) && loggedIn) {
    const url = req.nextUrl.clone()
    url.pathname = "/dashboard"
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/",
    "/login",
    "/dashboard/:path*",
    "/items/:path*",
    "/lists/:path*",
    "/settings/:path*",
  ],
}
