'use client';
import React, { useState } from 'react';

export default function AdminLogin() {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      const data = await res.json();
      if (res.ok) {
        window.location.reload();
      } else {
        setError(data.error || 'invalid');
      }
    } catch (err: any) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 480 }}>
      <h3>Admin login</h3>
      <form onSubmit={submit}>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="admin password" />
        <button type="submit" disabled={loading} style={{ marginLeft: 8 }}>{loading ? '…' : 'Login'}</button>
      </form>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <p>Use the `ADMIN_PASSWORD` environment variable in development.</p>
    </div>
  );
}
