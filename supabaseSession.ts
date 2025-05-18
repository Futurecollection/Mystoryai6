import { SupabaseClient } from '@supabase/supabase-js';
import { Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';

export interface SupabaseSessionData {
  [key: string]: any;
}

export class SupabaseSession {
  constructor(public data: SupabaseSessionData = {}, public sessionId: string) {}
}

export class SupabaseSessionInterface {
  constructor(
    private supabase: SupabaseClient,
    private tableName: string = 'flask_sessions',
    private sessionLifetimeMs: number = 7 * 24 * 60 * 60 * 1000 // 7 days
  ) {}

  async openSession(req: Request): Promise<SupabaseSession> {
    const cookieName = (req.app.get('SESSION_COOKIE_NAME') as string) || 'session';
    let sessionId = req.cookies[cookieName];
    if (!sessionId) {
      sessionId = uuidv4();
      return new SupabaseSession({}, sessionId);
    }

    const { data, error } = await this.supabase
      .from(this.tableName)
      .select('data, expiry')
      .eq('session_id', sessionId)
      .single();

    if (error || !data) {
      return new SupabaseSession({}, sessionId);
    }

    const expiry = data.expiry ? new Date(data.expiry) : null;
    if (expiry && expiry.getTime() < Date.now()) {
      return new SupabaseSession({}, sessionId);
    }

    return new SupabaseSession(data.data || {}, sessionId);
  }

  async saveSession(res: Response, session: SupabaseSession) {
    const cookieName = (res.app.get('SESSION_COOKIE_NAME') as string) || 'session';
    const expiry = new Date(Date.now() + this.sessionLifetimeMs);

    if (!session || Object.keys(session.data).length === 0) {
      await this.supabase.from(this.tableName).delete().eq('session_id', session.sessionId);
      res.clearCookie(cookieName);
      return;
    }

    await this.supabase.from(this.tableName).upsert({
      session_id: session.sessionId,
      data: session.data,
      expiry: expiry.toISOString(),
    });

    res.cookie(cookieName, session.sessionId, {
      expires: expiry,
      httpOnly: true,
    });
  }
}

