/**
 * JURIS AI — ADMIN PORTAL MIDDLEWARE
 *
 * Server-side route protection for all /admin/* routes.
 *
 * Flow:
 *  - /admin/login and /admin/auth/* are public (no redirect).
 *  - All other /admin/* routes require a valid server session.
 *  - The middleware calls GET /auth/me on the backend with the cookie.
 *  - If unauthenticated → redirect to /admin/login.
 *  - If authenticated but not ADMIN/SUPER_ADMIN → redirect to /admin/login.
 *
 * IMPORTANT: This is Next.js Edge Middleware — no Node.js-only APIs.
 * The HttpOnly session cookie is forwarded automatically when credentials:include.
 */

import { NextRequest, NextResponse } from 'next/server';

const PUBLIC_PATHS = [
  '/admin/login',
  '/admin/auth',
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(p => pathname.startsWith(p));
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths through without auth check
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  // Only guard /admin/* routes
  if (!pathname.startsWith('/admin')) {
    return NextResponse.next();
  }

  // Forward the session cookie to the backend
  const cookieHeader = request.headers.get('cookie') ?? '';

  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { cookie: cookieHeader },
      // Edge runtime doesn't support cache: 'no-store' directly — use cache control headers
      cache: 'no-store',
    });

    if (!res.ok) {
      // Not authenticated
      const loginUrl = new URL('/admin/login', request.url);
      loginUrl.searchParams.set('next', pathname);
      return NextResponse.redirect(loginUrl);
    }

    const user = await res.json() as {
      role: string;
      is_active?: boolean;
    };

    // Ensure account is active
    if (user.is_active === false) {
      const loginUrl = new URL('/admin/login', request.url);
      loginUrl.searchParams.set('error', 'account_disabled');
      return NextResponse.redirect(loginUrl);
    }

    // Enforce admin role
    const role = user.role as string;
    if (role !== 'admin' && role !== 'super_admin') {
      const loginUrl = new URL('/admin/login', request.url);
      loginUrl.searchParams.set('error', 'insufficient_role');
      return NextResponse.redirect(loginUrl);
    }

    return NextResponse.next();
  } catch {
    // Backend unreachable — fail closed
    const loginUrl = new URL('/admin/login', request.url);
    loginUrl.searchParams.set('error', 'auth_error');
    return NextResponse.redirect(loginUrl);
  }
}

export const config = {
  matcher: [
    '/admin/:path*',
  ],
};
