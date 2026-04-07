import { NextRequest, NextResponse } from "next/server";
import { createSupabaseMiddlewareClient } from "@/lib/supabase-middleware";

export async function proxy(request: NextRequest) {
  const { supabase, response } = createSupabaseMiddlewareClient(request);

  // getUser() validates the JWT against Supabase Auth servers.
  // Never use getSession() here — it does not revalidate the token.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/admin")) {
    if (!user) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Return the response so Set-Cookie headers from session refresh are
  // forwarded to the browser.
  return response;
}

export const config = {
  matcher: ["/admin/:path*", "/auth/callback"],
};
