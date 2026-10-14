'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Scale, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

import { getApiBaseUrl } from '@/lib/apiClient';

function UserCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const code = searchParams.get('code');
  const errorParam = searchParams.get('error');
  const stateParam = searchParams.get('state');

  const paramError = errorParam
    ? `Authentication declined: ${errorParam}`
    : !code
    ? 'Authorization code missing from identity provider callback.'
    : null;

  const [asyncStatus, setAsyncStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [asyncError, setAsyncError] = useState<string>('');

  const status = paramError ? 'error' : asyncStatus;
  const errorMessage = paramError || asyncError;

  useEffect(() => {
    if (paramError || !code) {
      return;
    }

    let active = true;

    const processOAuth = async () => {
      try {
        const backendUrl = getApiBaseUrl();
        const currentRedirectUri = typeof window !== 'undefined'
          ? `${window.location.origin}${window.location.pathname}`
          : 'http://localhost:3002/auth/google/callback';
        const callbackEndpoint = `${backendUrl}/auth/google/callback?code=${encodeURIComponent(code)}&redirect_uri=${encodeURIComponent(currentRedirectUri)}${stateParam ? `&state=${encodeURIComponent(stateParam)}` : ''}`;

        const res = await fetch(callbackEndpoint, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Accept': 'application/json',
          },
        });

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Identity verification failed at backend.');
        }

        if (!active) return;
        setAsyncStatus('success');

        let targetPath = '/home';
        const storedPath = window.sessionStorage.getItem('oauth_return_path');
        window.sessionStorage.removeItem('oauth_return_path');
        if (storedPath?.startsWith('/') && !storedPath.startsWith('//')) {
          targetPath = storedPath;
        }

        setTimeout(() => {
          if (active) {
            router.push(targetPath);
          }
        }, 1000);
      } catch (err: any) {
        if (!active) return;
        setAsyncStatus('error');
        setAsyncError(err.message || 'Verification error during authentication exchange.');
      }
    };

    processOAuth();

    return () => {
      active = false;
    };
  }, [code, stateParam, paramError, router]);

  return (
    <div className="min-h-screen bg-[#F0F4F8] flex flex-col justify-center items-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-lg border border-slate-200/80 p-8 text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-blue-50 border border-blue-100 mb-6">
          <Scale className="w-7 h-7 text-blue-700" />
        </div>

        {status === 'processing' && (
          <>
            <div className="flex justify-center mb-4">
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900 mb-2">
              Authenticating User Identity
            </h2>
            <p className="text-sm text-slate-600">
              Verifying Google OAuth credentials and establishing secure workspace session...
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="flex justify-center mb-4">
              <CheckCircle2 className="w-10 h-10 text-emerald-600" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900 mb-2">
              Authentication Successful
            </h2>
            <p className="text-sm text-slate-600">
              Session established. Redirecting to legal research portal...
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="flex justify-center mb-4">
              <AlertCircle className="w-10 h-10 text-amber-600" />
            </div>
            <h2 className="text-xl font-semibold text-slate-900 mb-2">
              Authentication Notice
            </h2>
            <p className="text-sm text-amber-900 mb-6 bg-amber-50 p-4 rounded-xl border border-amber-200">
              {errorMessage}
            </p>
            {errorMessage.includes('sign up first') ? (
              <a
                href="/signup"
                className="inline-flex items-center justify-center px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl text-sm transition-colors shadow-sm"
              >
                Go to Sign Up
              </a>
            ) : errorMessage.includes('already has a Juris AI account') ? (
              <a
                href="/login"
                className="inline-flex items-center justify-center px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl text-sm transition-colors shadow-sm"
              >
                Go to Sign In
              </a>
            ) : (
              <a
                href="/login"
                className="inline-flex items-center justify-center px-5 py-2.5 bg-slate-800 hover:bg-slate-900 text-white font-medium rounded-xl text-sm transition-colors shadow-sm"
              >
                Return to Login
              </a>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function UserOAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#F0F4F8] flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      }
    >
      <UserCallbackContent />
    </Suspense>
  );
}
