import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * JURIS AI — USER PORTAL MIDDLEWARE
 *
 * Edge routing middleware for User Legal Research Portal.
 * Cross-domain session cookies (stored on *.onrender.com) are validated
 * client-side by AuthContext via credentialed /auth/me fetches in the browser.
 */

export function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
