import { NextResponse, type NextRequest } from "next/server"

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/items",
  "/lists",
  "/settings",
  "/categories",
  "/locations",
  "/scan",
  "/statistics",
  "/notifications",
  "/collaboration",
]
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

  if (isProtected(pathname) && !loggedIn) {
    const url = req.nextUrl.clone()
    url.pathname = "/login"
    return NextResponse.redirect(url)
  }

  if (pathname === "/" && loggedIn) {
    const url = req.nextUrl.clone()
    url.pathname = "/dashboard"
    return NextResponse.redirect(url)
  }

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
    "/categories/:path*",
    "/locations/:path*",
    "/scan/:path*",
    "/statistics/:path*",
    "/notifications/:path*",
    "/collaboration/:path*",
  ],
}
