'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Scale,
  Lock,
  ShieldCheck,
  Server,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { getGoogleLoginUrl } from '@/lib/authClient';

const ERROR_MESSAGES: Record<string, string> = {
  insufficient_role: 'This Google account does not have administrator access. Contact a Super Administrator.',
  account_disabled: 'Your administrator account has been disabled. Contact a Super Administrator.',
  auth_error: 'Authentication service is temporarily unavailable. Please try again.',
  access_denied: 'Sign-in was cancelled.',
};

function AdminLoginContent() {
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const errorCode = searchParams.get('error');
    if (errorCode && ERROR_MESSAGES[errorCode]) {
      setErrorMessage(ERROR_MESSAGES[errorCode]);
    }
  }, [searchParams]);

  const handleGoogleSignIn = () => {
    setIsLoading(true);
    setErrorMessage(null);
    const nextPath = searchParams.get('next') ?? '/admin';
    window.location.href = getGoogleLoginUrl(nextPath);
  };

  return (
    <div className="min-h-screen bg-[#E7EDF4] flex flex-col justify-center items-center p-4 md:p-8">
      <div className="w-full max-w-4xl bg-[#FFFFFF] rounded-2xl border border-[#C9D4E1] shadow-[0_8px_40px_rgba(23,37,58,0.14)] overflow-hidden grid grid-cols-1 lg:grid-cols-12">
        {/* LEFT COLUMN: Identity & Product Context */}
        <div className="lg:col-span-5 bg-[#183B5B] text-white p-8 lg:p-10 flex flex-col justify-between relative overflow-hidden">
          {/* Subtle background glow */}
          <div className="absolute -right-16 -bottom-16 w-64 h-64 bg-[#2563A8]/20 rounded-full blur-2xl pointer-events-none" />

          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2.5 rounded-xl bg-[#2563A8] text-white shadow-sm shrink-0">
                <Scale className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold font-serif leading-tight">Juris AI</h1>
                <span className="font-mono text-[10px] text-[#3B82D0] font-bold tracking-widest uppercase">
                  ADMIN CONSOLE
                </span>
              </div>
            </div>

            <p className="text-sm text-[#D9E7F5]/90 font-sans leading-relaxed mt-4">
              Administrative access to the Juris AI legal intelligence platform.
              Sign in with your provisioned Google account.
            </p>
          </div>

          <div className="mt-8 lg:mt-0 pt-6 border-t border-[#3B82D0]/30 space-y-3">
            <div className="flex items-center gap-2.5 text-xs text-[#D9E7F5]">
              <ShieldCheck className="h-4 w-4 text-[#3B82D0] shrink-0" />
              <span>Role-Based Access Control (RBAC)</span>
            </div>
            <div className="flex items-center gap-2.5 text-xs text-[#D9E7F5]">
              <Server className="h-4 w-4 text-[#3B82D0] shrink-0" />
              <span>Server-Side Session Authentication</span>
            </div>
            <div className="flex items-center gap-2.5 text-xs text-[#D9E7F5]">
              <Lock className="h-4 w-4 text-[#3B82D0] shrink-0" />
              <span>Audit Logging &amp; System Telemetry</span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Authentication Card */}
        <div className="lg:col-span-7 bg-[#F5F7FA] p-8 lg:p-10 flex flex-col justify-center border-t lg:border-t-0 lg:border-l border-[#C9D4E1]">
          <div className="mb-8">
            <h2 className="text-2xl font-serif font-bold text-[#17253A]">Administrator Sign In</h2>
            <p className="text-xs text-[#526176] mt-1.5 font-sans leading-relaxed">
              Sign in with your provisioned Google Workspace account to access admin controls.
              Access is granted by role — your Google identity is verified by our secure backend.
            </p>
          </div>

          {errorMessage && (
            <div className="mb-6 p-3.5 rounded-lg bg-[#FEE2E2] border border-[#E8B8B8] text-[#8B2E2E] text-xs font-sans flex items-start gap-2.5">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{errorMessage}</span>
            </div>
          )}

          {/* Google Sign-In Button */}
          <button
            id="admin-google-signin-btn"
            onClick={handleGoogleSignIn}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 h-12 px-6 bg-white border border-[#C9D4E1] rounded-xl shadow-sm hover:bg-[#F0F4F8] hover:border-[#2563A8] transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed group"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 text-[#526176] animate-spin" />
            ) : (
              /* Google SVG logo */
              <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
            )}
            <span className="text-sm font-semibold text-[#17253A]">
              {isLoading ? 'Redirecting to Google…' : 'Continue with Google'}
            </span>
          </button>

          <div className="mt-6 pt-4 border-t border-[#D9E1EA] space-y-2">
            <p className="text-[11px] font-mono text-[#718096] text-center">
              Authorized access only. Your role is determined by the administrator database.
            </p>
            <p className="text-[11px] font-mono text-[#718096] text-center">
              Contact your Super Administrator to request access.
            </p>
          </div>

          <div className="mt-4 flex items-center justify-between text-[11px] font-mono text-[#718096]">
            <span>Juris AI Admin Console</span>
            <span>v0.10.6</span>
          </div>
        </div>
      </div>

      <div className="mt-6 text-center text-xs text-[#718096] font-mono">
        Juris AI Legal Intelligence Platform &bull; System Administration
      </div>
    </div>
  );
}

export default function AdminLoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#E7EDF4] flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#2563A8]" />
        </div>
      }
    >
      <AdminLoginContent />
    </Suspense>
  );
}
