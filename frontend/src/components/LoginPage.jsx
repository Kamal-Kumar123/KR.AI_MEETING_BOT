import React, { useCallback, useEffect, useRef, useState } from 'react';
import Header from './Header';
import { useAuth } from '../context/AuthContext';
import { GOOGLE_CLIENT_ID } from '../lib/api';

const REGISTERED_KEY = 'krai_has_registered';

function hasRegisteredBefore() {
  return localStorage.getItem(REGISTERED_KEY) === 'true';
}

function markRegistered() {
  localStorage.setItem(REGISTERED_KEY, 'true');
}

function LoginPage() {
  const { signIn, signUp, signInWithGoogle, user, loading } = useAuth();
  const [tab, setTab] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);
  const googleBtnRef = useRef(null);

  useEffect(() => {
    if (!loading && user) {
      window.location.href = '/meetings';
    }
  }, [user, loading]);

  const handleGoogleCredential = useCallback(
    async (credential) => {
      setError('');
      setSuccess('');
      setBusy(true);
      try {
        await signInWithGoogle(credential);
        markRegistered();
        window.location.href = '/meetings';
      } catch (err) {
        setError(err.response?.data?.detail || 'Google authentication failed.');
      } finally {
        setBusy(false);
      }
    },
    [signInWithGoogle]
  );

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    const renderGoogleButton = () => {
      if (!window.google?.accounts?.id || !googleBtnRef.current) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (response) => handleGoogleCredential(response.credential),
      });
      googleBtnRef.current.innerHTML = '';
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'filled_blue',
        size: 'large',
        text: tab === 'register' ? 'signup_with' : 'signin_with',
        width: 320,
      });
      setGoogleReady(true);
    };

    if (window.google?.accounts?.id) {
      renderGoogleButton();
      return;
    }

    const existing = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    if (existing) {
      existing.addEventListener('load', renderGoogleButton);
      return () => existing.removeEventListener('load', renderGoogleButton);
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.onload = renderGoogleButton;
    document.body.appendChild(script);
  }, [GOOGLE_CLIENT_ID, tab, handleGoogleCredential]);

  const switchToLogin = () => {
    setError('');
    setSuccess('');
    setTab('login');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setBusy(true);
    try {
      if (tab === 'login') {
        await signIn(email.trim(), password);
      } else {
        if (password.length < 8) {
          setError('Password must be at least 8 characters.');
          setBusy(false);
          return;
        }
        if (!fullName.trim()) {
          setError('Please enter your full name.');
          setBusy(false);
          return;
        }
        await signUp(email.trim(), password, fullName.trim());
        markRegistered();
        setSuccess('Account created! Redirecting to your meetings…');
      }
      window.location.href = '/meetings';
    } catch (err) {
      const detail = err.response?.data?.detail || '';
      if (tab === 'register' && typeof detail === 'string' && detail.toLowerCase().includes('already registered')) {
        markRegistered();
        setTab('login');
        setError('This email is already registered. Please login instead.');
      } else {
        setError(detail || 'Authentication failed.');
      }
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f172a] text-gray-200 flex items-center justify-center">
        Loading…
      </div>
    );
  }

  return (
    <div className="bg-[#0f172a] text-gray-200 min-h-screen flex flex-col">
      <Header showAuth={false} />
      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md p-8 rounded-xl border border-gray-700 bg-gray-900/50 shadow-xl">
          <h1 className="text-2xl font-bold text-center mb-2">Welcome to KR.AI BOT</h1>
          <p className="text-sm text-gray-400 text-center mb-6">
            {tab === 'register'
              ? 'Create an account to access your extension meetings'
              : 'Welcome back — sign in to your account'}
          </p>

          <div className="flex mb-6 rounded-lg overflow-hidden border border-gray-700">
            <button
              type="button"
              onClick={() => {
                setError('');
                setSuccess('');
                setTab('register');
              }}
              className={`flex-1 py-2 text-sm font-medium ${tab === 'register' ? 'bg-purple-700 text-white' : 'bg-gray-800 text-gray-400'}`}
            >
              Sign Up
            </button>
            <button
              type="button"
              onClick={switchToLogin}
              className={`flex-1 py-2 text-sm font-medium ${tab === 'login' ? 'bg-purple-700 text-white' : 'bg-gray-800 text-gray-400'}`}
            >
              Login
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {tab === 'register' && (
              <div>
                <label className="block text-sm mb-1">Full name</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-600 text-sm"
                  placeholder="Your name"
                />
              </div>
            )}
            <div>
              <label className="block text-sm mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-600 text-sm"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-600 text-sm"
                placeholder={tab === 'register' ? 'Min 8 characters' : 'Password'}
              />
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}
            {success && <p className="text-sm text-green-400">{success}</p>}

            <button
              type="submit"
              disabled={busy}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 py-2 rounded font-medium"
            >
              {busy ? 'Please wait…' : tab === 'login' ? 'Login' : 'Create account'}
            </button>
          </form>

          <div className="mt-6">
            <p className="text-xs text-gray-500 text-center mb-3">
              {tab === 'register' ? 'or sign up with Google' : 'or sign in with Google'}
            </p>
            {GOOGLE_CLIENT_ID ? (
              <div className="flex justify-center min-h-[44px]" ref={googleBtnRef} />
            ) : (
              <p className="text-xs text-red-400 text-center">
                Google Sign-In not configured. Set REACT_APP_GOOGLE_CLIENT_ID in frontend/.env
              </p>
            )}
            {GOOGLE_CLIENT_ID && !googleReady && (
              <p className="text-xs text-gray-500 text-center mt-2">Loading Google Sign-In…</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default LoginPage;
