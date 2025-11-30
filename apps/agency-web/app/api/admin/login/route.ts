import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { password } = body || {};
    const ADMIN = process.env.ADMIN_PASSWORD || '';
    if (!ADMIN) {
      return NextResponse.json({ error: 'admin password not configured' }, { status: 500 });
    }
    if (password !== ADMIN) {
      return NextResponse.json({ error: 'invalid' }, { status: 401 });
    }

    const res = NextResponse.json({ ok: true });
    res.cookies.set('admin_auth', password, { httpOnly: true, path: '/', maxAge: 60 * 60 * 24 });
    return res;
  } catch (err: any) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
