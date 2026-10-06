import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * JURIS AI — ADMIN PORTAL MIDDLEWARE
 *
 * Edge routing middleware for Admin Portal.
 * Cross-domain session cookies (stored on *.onrender.com) are validated
 * client-side by useRequireAdmin / AuthContext via credentialed /auth/me fetches in the browser.
 */

export function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/admin/:path*',
  ],
};
