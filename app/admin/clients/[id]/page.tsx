import React from 'react';
import prisma from '../../../../src/lib/prisma';
import { cookies } from 'next/headers';
import AdminLogin from '../../components/AdminLogin';

type Props = {
  params: { id: string };
};

export default async function ClientPage({ params }: Props) {
  const { id } = params;
  const adminCookie = cookies().get('admin_auth')?.value || null;
  const ADMIN = process.env.ADMIN_PASSWORD || null;
  if (ADMIN && adminCookie !== ADMIN) {
    return (
      <div style={{ padding: 24 }}>
        <h1>Admin</h1>
        <p>Protected admin area — please login.</p>
        {/* @ts-expect-error Server -> Client */}
        <AdminLogin />
      </div>
    );
  }

  const client = await prisma.client.findUnique({
    where: { id },
    include: { intakeSubmissions: true, clientConfigs: true, generatedDocuments: true },
  });

  if (!client) {
    return <div style={{ padding: 24 }}><h1>Client not found</h1></div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>{client.name}</h1>
      <p><strong>Website:</strong> {client.website}</p>
      <p><strong>Industry:</strong> {client.industry}</p>

      {/* @ts-expect-error Server -> Client */}
      <Generators clientId={client.id} />


      <section>
        <h2>Intake Submissions</h2>
        <ul>
          {client.intakeSubmissions.map(s => (
            <li key={s.id}>
              {new Date(s.submittedAt).toLocaleString()} — <details><summary>Raw</summary><pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(s.raw, null, 2)}</pre></details>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Client Configs</h2>
        {client.clientConfigs.map(cfg => (
          <div key={cfg.id} style={{ border: '1px solid #eee', padding: 12, marginBottom: 8 }}>
            <div><strong>version:</strong> {cfg.version} <em>normalized: {new Date(cfg.normalizedAt).toLocaleString()}</em></div>
            <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(cfg.config, null, 2)}</pre>
          </div>
        ))}
      </section>

      <section>
        <h2>Generated Documents</h2>
        <ul>
          {client.generatedDocuments.map(d => (
            <li key={d.id}><strong>{d.type}</strong> — {new Date(d.createdAt).toLocaleString()}<pre>{d.content}</pre></li>
          ))}
        </ul>
      </section>
    </div>
  );
}
