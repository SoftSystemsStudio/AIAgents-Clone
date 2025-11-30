import { NextResponse } from 'next/server';
import prisma from '../../../../../src/lib/prisma';
import { generateFromLLM } from '../../../../../src/lib/llm';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { clientId, clientConfig } = body || {};

    let config = clientConfig;
    if (!config) {
      if (!clientId) return NextResponse.json({ error: 'clientId or clientConfig required' }, { status: 400 });
      const cfg = await prisma.clientConfig.findFirst({ where: { clientId }, orderBy: { normalizedAt: 'desc' } });
      if (!cfg) return NextResponse.json({ error: 'client config not found' }, { status: 404 });
      config = cfg.config;
    }

    const systemPrompt = `You are an expert consultant writing client-facing proposals for AI automation projects. Given the client's configuration JSON, produce a clear, persuasive proposal suitable for sending to a decision-maker. Include scope, deliverables, timeline (30/60/90 day phases), assumptions, and a high-level price estimate tied to the client's stated budget range.`;

    const userPrompt = `Client configuration (JSON):\n\n${JSON.stringify(config, null, 2)}\n\nProduce a client-facing proposal with:\n- Short executive summary\n- Scope and deliverables\n- 30/60/90 day milestones\n- Clear assumptions and out-of-scope items\n- Pricing estimate (use client's budget ranges)\nProvide the proposal in markdown format.`;

    const content = await generateFromLLM({ systemPrompt, userPrompt, maxTokens: 1400 });

    const saved = await prisma.generatedDocument.create({
      data: { clientId: clientId || (config.company_profile?.name ?? 'unknown'), type: 'proposal', content, meta: { generatedAt: new Date().toISOString() } },
    }).catch(async () => ({ id: 'unpersisted' } as any));

    return NextResponse.json({ content, docId: saved.id || null }, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
