'use client';
import React, { useState } from 'react';

type Props = { clientId: string };

export default function Generators({ clientId }: Props) {
  const [brief, setBrief] = useState<string | null>(null);
  const [proposal, setProposal] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const call = async (type: 'brief' | 'proposal') => {
    setLoading(true);
    try {
      const res = await fetch(`/api/generate/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clientId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'generate failed');
      if (type === 'brief') setBrief(data.content);
      if (type === 'proposal') setProposal(data.content);
    } catch (err: any) {
      alert('Generation failed: ' + String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ marginTop: 16 }}>
      <h3>Generators</h3>
      <div>
        <button onClick={() => call('brief')} disabled={loading}>Generate Solution Brief</button>
        <button onClick={() => call('proposal')} disabled={loading} style={{ marginLeft: 8 }}>Generate Proposal</button>
      </div>

      {brief && (
        <div style={{ marginTop: 12, padding: 8, border: '1px solid #ddd' }}>
          <h4>Solution Brief</h4>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{brief}</pre>
        </div>
      )}

      {proposal && (
        <div style={{ marginTop: 12, padding: 8, border: '1px solid #ddd' }}>
          <h4>Proposal (Markdown)</h4>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{proposal}</pre>
        </div>
      )}
    </div>
  );
}
