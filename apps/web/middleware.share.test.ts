import { NextRequest } from "next/server"
import { expect, it } from "vitest"

import { config, middleware } from "./middleware"

it.each([false, true])("/share 不受登入狀態 %s 影響，不重導", loggedIn => {
  const request = new NextRequest("http://localhost/share", {
    headers: loggedIn ? { cookie: "ims_token=1" } : {},
  })
  const response = middleware(request)
  expect(response.headers.get("location")).toBeNull()
  expect(response.headers.get("x-middleware-next")).toBe("1")
  expect(config.matcher.some(value => value.includes("share"))).toBe(false)
})
