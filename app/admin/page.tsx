import React from 'react';
import prisma from '../../src/lib/prisma';
import Link from 'next/link';
import { cookies } from 'next/headers';
import AdminLogin from './components/AdminLogin';

export default async function AdminPage() {
  const adminCookie = cookies().get('admin_auth')?.value || null;
  const ADMIN = process.env.ADMIN_PASSWORD || null;
  if (ADMIN && adminCookie !== ADMIN) {
    return (
      <div style={{ padding: 24 }}>
        <h1>Admin</h1>
        <p>Protected admin area — please login.</p>
        {/* Client component */}
        {/* @ts-expect-error Server -> Client */}
        <AdminLogin />
      </div>
    );
  }

  const clients = await prisma.client.findMany({ orderBy: { createdAt: 'desc' }, take: 100 });

  return (
    <div style={{ padding: 24 }}>
      <h1>Admin — Clients</h1>
      <p>List of clients and quick links to their configs.</p>
      <ul>
        {clients.map(c => (
          <li key={c.id}>
            <strong>{c.name}</strong> — {c.website || 'no site'} — <Link href={`/admin/clients/${c.id}`}>view</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
