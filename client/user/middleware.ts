import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * JURIS AI — USER PORTAL MIDDLEWARE
 *
 * Route protection for User Legal Research Portal.
 * Public routes: /login, /auth/*
 * Protected routes: /home, /research, /documents, /citations, /history, /settings, /
 */

const PUBLIC_PATH_PREFIXES = ['/login', '/auth', '/_next', '/favicon.ico', '/api'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublic = PUBLIC_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );

  if (isPublic) {
    return NextResponse.next();
  }

  // Check backend session
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const cookieHeader = request.headers.get('cookie') || '';

  try {
    const authRes = await fetch(`${backendUrl}/auth/me`, {
      method: 'GET',
      headers: {
        cookie: cookieHeader,
        Accept: 'application/json',
      },
      cache: 'no-store',
    });

    if (!authRes.ok) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('from', pathname);
      return NextResponse.redirect(loginUrl);
    }

    const userData = await authRes.json();
    const user = userData.user || userData;

    if (!user || !user.id) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('from', pathname);
      return NextResponse.redirect(loginUrl);
    }

    return NextResponse.next();
  } catch {
    // If backend is offline or unreachable, allow soft fallback with client-side auth check
    return NextResponse.next();
  }
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
