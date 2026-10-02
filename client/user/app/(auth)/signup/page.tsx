'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Scale,
  ShieldCheck,
  BookOpen,
  Search,
  Sparkles,
  AlertCircle,
  Loader2,
  LogIn,
} from 'lucide-react';
import { getGoogleLoginUrl } from '@/lib/authClient';

function UserSignUpContent() {
  const searchParams = useSearchParams();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isAccountExists, setIsAccountExists] = useState(false);
  const [isRedirecting, setIsRedirecting] = useState(false);

  useEffect(() => {
    const errorParam = searchParams.get('error');
    if (errorParam === 'account_exists' || errorParam === 'This Google account already has a Juris AI account. Please sign in.') {
      setIsAccountExists(true);
      setErrorMsg('This Google account already has a Juris AI account. Please sign in.');
    } else if (errorParam) {
      setErrorMsg(decodeURIComponent(errorParam));
    }
  }, [searchParams]);

  const handleGoogleSignUp = () => {
    setIsRedirecting(true);
    const from = searchParams.get('from') || '/home';
    const loginUrl = getGoogleLoginUrl(from, 'signup');
    window.location.href = loginUrl;
  };

  return (
    <div className="min-h-screen bg-[#F0F4F8] flex flex-col justify-center items-center p-4 sm:p-6 lg:p-8">
      <div className="max-w-md w-full">
        {/* Logo & Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 text-white shadow-xl shadow-blue-500/20 mb-4">
            <Scale className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Juris AI Legal Research Portal
          </h1>
          <p className="text-slate-600 text-sm mt-1">
            Create your account to start legal research for Indian law
          </p>
        </div>

        {/* Auth Card */}
        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/80 p-8">
          {errorMsg && (
            <div className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200/80 text-amber-900 text-sm flex flex-col gap-3">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>{errorMsg}</div>
              </div>
              {isAccountExists && (
                <Link
                  href="/login"
                  className="mt-1 w-full flex items-center justify-center gap-2 py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-xs transition-colors"
                >
                  <LogIn className="w-4 h-4" />
                  <span>Go to Sign In</span>
                </Link>
              )}
            </div>
          )}

          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-lg font-semibold text-slate-900">Create Your Account</h2>
              <p className="text-xs text-slate-500 mt-1">
                Sign up with your Google account to get started
              </p>
            </div>

            {/* Google OAuth Button */}
            <button
              onClick={handleGoogleSignUp}
              disabled={isRedirecting}
              className="w-full flex items-center justify-center gap-3 py-3 px-4 bg-white hover:bg-slate-50 text-slate-700 font-medium border border-slate-300 rounded-xl shadow-sm transition-all duration-150 disabled:opacity-60 cursor-pointer"
            >
              {isRedirecting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                  <span>Redirecting to Google...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                  <span>Sign Up with Google</span>
                </>
              )}
            </button>

            <div className="text-center pt-2">
              <span className="text-xs text-slate-500">Already have an account? </span>
              <Link href="/login" className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline">
                Sign In
              </Link>
            </div>

            {/* Platform feature badges */}
            <div className="pt-4 border-t border-slate-100 grid grid-cols-3 gap-2 text-center text-xs text-slate-500">
              <div className="flex flex-col items-center gap-1">
                <BookOpen className="w-4 h-4 text-blue-600" />
                <span>Statute Graph</span>
              </div>
              <div className="flex flex-col items-center gap-1">
                <Search className="w-4 h-4 text-blue-600" />
                <span>Precedent RAG</span>
              </div>
              <div className="flex flex-col items-center gap-1">
                <Sparkles className="w-4 h-4 text-blue-600" />
                <span>Verified Citations</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="mt-6 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Public accounts are assigned standard USER privileges</span>
        </div>
      </div>
    </div>
  );
}

export default function UserSignUpPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#F0F4F8] flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      }
    >
      <UserSignUpContent />
    </Suspense>
  );
}
