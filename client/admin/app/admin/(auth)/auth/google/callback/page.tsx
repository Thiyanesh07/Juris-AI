'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Scale, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

const envApiUrl = process.env.NEXT_PUBLIC_API_URL;
const API_BASE = (envApiUrl && envApiUrl.trim())
  ? envApiUrl.trim().replace(/\/+$/, '')
  : (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1')
  ? 'https://juris-ai-fhjw.onrender.com'
  : 'http://localhost:8000';

type Status = 'processing' | 'success' | 'error';

function AdminGoogleCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<Status>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');

    if (error) {
      setErrorMessage(
        error === 'access_denied'
          ? 'Sign-in was cancelled.'
          : `Google returned an error: ${error}`
      );
      setStatus('error');
      return;
    }

    if (!code) {
      setErrorMessage('Missing authorization code from Google.');
      setStatus('error');
      return;
    }

    // Forward the code + state to the backend for secure server-side exchange
    const currentRedirectUri = typeof window !== 'undefined'
      ? `${window.location.origin}${window.location.pathname}`
      : 'http://localhost:3001/admin/auth/google/callback';
    const params = new URLSearchParams({ code, redirect_uri: currentRedirectUri, ...(state ? { state } : {}) });
    const backendCallback = `${API_BASE}/auth/google/callback?${params.toString()}`;

    fetch(backendCallback, {
      credentials: 'include',
      redirect: 'manual',
    })
      .then(async (res) => {
        if (res.ok || res.status === 0 /* opaque redirect */) {
          const meRes = await fetch(`${API_BASE}/auth/me`, {
            credentials: 'include',
          });
          if (!meRes.ok) {
            setErrorMessage('Authentication failed. Please try again.');
            setStatus('error');
            return;
          }
          const user = await meRes.json() as { role: string };
          if (user.role !== 'admin' && user.role !== 'super_admin') {
            setErrorMessage(
              'Your account does not have administrator access. Contact a Super Administrator to grant access.'
            );
            setStatus('error');
            return;
          }
          setStatus('success');
          setTimeout(() => router.replace('/admin'), 800);
        } else {
          const data = await res.json().catch(() => null);
          setErrorMessage(
            (data as { detail?: string } | null)?.detail ?? 'Authentication failed. Please try again.'
          );
          setStatus('error');
        }
      })
      .catch(() => {
        setErrorMessage('Could not reach the authentication server. Please try again.');
        setStatus('error');
      });
  }, [searchParams, router]);

  return (
    <div className="min-h-screen bg-[#E7EDF4] flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-sm bg-white rounded-2xl border border-[#C9D4E1] shadow-lg p-8 text-center space-y-5">
        {/* Brand */}
        <div className="flex items-center justify-center gap-2.5 mb-2">
          <div className="p-2 rounded-lg bg-[#2563A8] text-white">
            <Scale className="h-5 w-5" />
          </div>
          <span className="font-serif font-bold text-[#17253A] text-lg">Juris AI</span>
        </div>

        {status === 'processing' && (
          <>
            <Loader2 className="h-8 w-8 text-[#2563A8] animate-spin mx-auto" />
            <div>
              <p className="text-sm font-semibold text-[#17253A]">Verifying your identity…</p>
              <p className="text-xs text-[#526176] mt-1">Please wait while we complete sign-in.</p>
            </div>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle2 className="h-8 w-8 text-[#1E6B45] mx-auto" />
            <div>
              <p className="text-sm font-semibold text-[#17253A]">Authentication successful</p>
              <p className="text-xs text-[#526176] mt-1">Redirecting to Admin Dashboard…</p>
            </div>
          </>
        )}

        {status === 'error' && (
          <>
            <AlertCircle className="h-8 w-8 text-[#8B2E2E] mx-auto" />
            <div>
              <p className="text-sm font-semibold text-[#17253A]">Sign-in failed</p>
              <p className="text-xs text-[#526176] mt-1 leading-relaxed">{errorMessage}</p>
            </div>
            <button
              onClick={() => (window.location.href = '/admin/login')}
              className="w-full h-9 rounded-lg bg-[#183B5B] text-white text-sm font-semibold hover:bg-[#2563A8] transition-colors"
            >
              Return to Sign In
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function AdminGoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#E7EDF4] flex items-center justify-center">
          <Loader2 className="h-8 w-8 text-[#2563A8] animate-spin" />
        </div>
      }
    >
      <AdminGoogleCallbackContent />
    </Suspense>
  );
}
