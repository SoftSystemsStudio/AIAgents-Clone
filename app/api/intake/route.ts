import { NextResponse } from 'next/server';
import prisma from '../../../src/lib/prisma';
import { deriveClientConfig } from '../../../src/lib/normalize';

export async function POST(request: Request) {
  try {
    const payload = await request.json();

    // Persist raw intake submission
    const clientName = payload.company_profile?.name;

    let client = null;
    if (clientName) {
      client = await prisma.client.create({
        data: {
          id: undefined as any,
          name: clientName,
          website: payload.company_profile?.website || null,
          industry: payload.company_profile?.industry || null,
          size: payload.company_profile?.size || null,
          businessModel: payload.company_profile?.business_model || null,
          primaryContactName: payload.primary_contact?.name || null,
          primaryContactEmail: payload.primary_contact?.email || null,
        },
      });
    }

    const submission = await prisma.intakeSubmission.create({
      data: {
        clientId: client ? client.id : null,
        raw: payload,
        sourceUrl: payload.sourceUrl || null,
      },
    });

    // Derive normalized config
    const normalized = deriveClientConfig(payload);

    const clientConfig = await prisma.clientConfig.create({
      data: {
        clientId: client ? client.id : submission.id, // if no client, link to submission id placeholder
        config: normalized,
        derivedFromSubmissionId: submission.id,
      },
    });

    return NextResponse.json({ submissionId: submission.id, clientConfig }, { status: 201 });
  } catch (err: any) {
    // eslint-disable-next-line no-console
    console.error('intake submit error', err);
    return NextResponse.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
