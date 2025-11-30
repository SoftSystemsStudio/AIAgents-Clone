import { NextResponse } from 'next/server';
import prisma from '../../../../src/lib/prisma';
import { generateFromLLM } from '../../../../src/lib/llm';

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

    const systemPrompt = `You are an expert AI solution architect. Given the client's configuration JSON, produce a concise solution brief describing the current state, recommended systems, and a pragmatic Phase 1/2/3 implementation plan targeted for early delivery and minimal risk.`;

    const userPrompt = `Client configuration (JSON):\n\n${JSON.stringify(config, null, 2)}\n\nProduce:\n1) One-paragraph executive summary.\n2) Recommended system architecture (short bullets).\n3) Phase 1 (MVP) - what to build in 30 days with estimated effort.\n4) Phase 2 and 3 high-level steps.\nKeep it concise and non-technical where possible for stakeholders.`;

    const content = await generateFromLLM({ systemPrompt, userPrompt, maxTokens: 1200 });

    const saved = await prisma.generatedDocument.create({
      data: { clientId: clientId || (config.company_profile?.name ?? 'unknown'), type: 'brief', content, meta: { generatedAt: new Date().toISOString() } },
    }).catch(async () => {
      // Attempt to create without clientId (if clientId not provided)
      return { id: 'unpersisted' } as any;
    });

    return NextResponse.json({ content, docId: saved.id || null }, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
