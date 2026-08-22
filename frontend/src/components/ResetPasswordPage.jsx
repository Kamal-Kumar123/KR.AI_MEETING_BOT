import React, { useState } from 'react';
import Header from './Header';
import { resetPassword, setAuth } from '../lib/api';

function ResetPasswordPage() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!token) {
      setError('Invalid reset link. Request a new password reset email.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setBusy(true);
    try {
      const data = await resetPassword(token, password);
      setAuth(data.access_token, '');
      setSuccess('Password updated! Redirecting…');
      setTimeout(() => {
        window.location.href = '/meetings';
      }, 1200);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not reset password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-[#0f172a] text-gray-200 min-h-screen flex flex-col">
      <Header showAuth={false} />
      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md p-8 rounded-xl border border-gray-700 bg-gray-900/50 shadow-xl">
          <h1 className="text-2xl font-bold text-center mb-2">Choose a new password</h1>
          <p className="text-sm text-gray-400 text-center mb-6">
            Enter a new password for your KRAI account.
          </p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm mb-1">New password</label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-600 text-sm"
                placeholder="Min 8 characters"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Confirm password</label>
              <input
                type="password"
                required
                minLength={8}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-600 text-sm"
                placeholder="Repeat password"
              />
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            {success && <p className="text-sm text-green-400">{success}</p>}
            <button
              type="submit"
              disabled={busy}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 py-2 rounded font-medium"
            >
              {busy ? 'Saving…' : 'Update password'}
            </button>
          </form>
          <p className="text-center mt-4">
            <a href="/" className="text-sm text-blue-400 hover:underline">
              Back to login
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}

export default ResetPasswordPage;
