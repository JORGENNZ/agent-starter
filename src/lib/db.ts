// SQLite para persistir sesiones de conversación entre reinicios.
// Mantén aquí SOLO lo de sesiones. Agrega tus propias tablas de dominio
// (clientes, pedidos, etc.) según necesites — pero NO mezcles dominio con sesiones.

import Database from 'better-sqlite3';
import * as path from 'path';

const DB_PATH = process.env.DB_PATH || path.join(process.cwd(), 'agent.db');
const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS sesiones (
    telefono TEXT PRIMARY KEY,
    messages TEXT NOT NULL,
    datos_cliente TEXT NOT NULL,
    extras TEXT,
    updated_at INTEGER NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_sesiones_updated ON sesiones(updated_at);
`);

export interface SesionDB {
  messages: any[];
  datos_cliente: Record<string, any>;
  extras?: any;
  updatedAt: number;
}

export function dbGetSesion(telefono: string): SesionDB | null {
  const row = db.prepare(`SELECT * FROM sesiones WHERE telefono=?`).get(telefono) as any;
  if (!row) return null;
  try {
    return {
      messages: JSON.parse(row.messages),
      datos_cliente: JSON.parse(row.datos_cliente),
      extras: row.extras ? JSON.parse(row.extras) : undefined,
      updatedAt: row.updated_at,
    };
  } catch {
    return null;
  }
}

export function dbSaveSesion(telefono: string, state: SesionDB): void {
  try {
    db.prepare(`
      INSERT OR REPLACE INTO sesiones (telefono, messages, datos_cliente, extras, updated_at)
      VALUES (?, ?, ?, ?, ?)
    `).run(
      telefono,
      JSON.stringify(state.messages),
      JSON.stringify(state.datos_cliente),
      state.extras ? JSON.stringify(state.extras) : null,
      state.updatedAt,
    );
  } catch (err: any) {
    console.error(`[DB SESION SAVE ERROR] ${telefono}:`, err.message);
  }
}

export function dbDeleteSesion(telefono: string): void {
  db.prepare(`DELETE FROM sesiones WHERE telefono=?`).run(telefono);
}

export function dbListSesiones(limit = 50): Array<{
  telefono: string;
  updated_at: number;
  num_mensajes: number;
  preview_user: string;
  preview_bot: string;
  datos_cliente: Record<string, any>;
}> {
  const rows = db.prepare(`SELECT * FROM sesiones ORDER BY updated_at DESC LIMIT ?`).all(limit) as any[];
  const out: any[] = [];
  for (const row of rows) {
    try {
      const messages: any[] = JSON.parse(row.messages);
      const datos = JSON.parse(row.datos_cliente);
      let lastUser = '', lastBot = '';
      for (let i = messages.length - 1; i >= 0; i--) {
        const m = messages[i];
        if (lastBot === '' && m.role === 'assistant') {
          lastBot = extractText(m.content).substring(0, 120);
        }
        if (lastUser === '' && m.role === 'user') {
          lastUser = extractText(m.content).substring(0, 120);
        }
        if (lastUser && lastBot) break;
      }
      out.push({
        telefono: row.telefono,
        updated_at: row.updated_at,
        num_mensajes: messages.length,
        preview_user: lastUser,
        preview_bot: lastBot,
        datos_cliente: datos,
      });
    } catch { /* skip */ }
  }
  return out;
}

export function dbGetConversacion(telefono: string): {
  telefono: string;
  updated_at: number;
  datos_cliente: Record<string, any>;
  mensajes: Array<{ role: string; texto: string; tool_use?: any; tool_result?: any }>;
} | null {
  const row = db.prepare(`SELECT * FROM sesiones WHERE telefono=?`).get(telefono) as any;
  if (!row) return null;
  try {
    const messages: any[] = JSON.parse(row.messages);
    const datos = JSON.parse(row.datos_cliente);
    const mensajes: any[] = [];
    for (const m of messages) {
      if (typeof m.content === 'string') {
        mensajes.push({ role: m.role, texto: m.content });
      } else if (Array.isArray(m.content)) {
        for (const c of m.content) {
          if (c.type === 'text') {
            mensajes.push({ role: m.role, texto: c.text || '' });
          } else if (c.type === 'tool_use') {
            mensajes.push({ role: m.role, texto: '', tool_use: { name: c.name, input: c.input } });
          } else if (c.type === 'tool_result') {
            const t = typeof c.content === 'string' ? c.content : JSON.stringify(c.content);
            mensajes.push({ role: m.role, texto: '', tool_result: { content: t.substring(0, 500) } });
          } else if (c.type === 'image') {
            mensajes.push({ role: m.role, texto: '[imagen recibida]' });
          } else if (c.type === 'document') {
            mensajes.push({ role: m.role, texto: '[PDF recibido]' });
          }
        }
      }
    }
    return { telefono: row.telefono, updated_at: row.updated_at, datos_cliente: datos, mensajes };
  } catch {
    return null;
  }
}

function extractText(content: any): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    for (const c of content) {
      if (c.type === 'text' && c.text) return c.text;
      if (c.type === 'tool_use') return `[tool: ${c.name}]`;
      if (c.type === 'image') return '[imagen]';
      if (c.type === 'document') return '[PDF]';
    }
  }
  return '';
}

export function dbCleanExpiredSesiones(ttlMs: number): number {
  const cutoff = Date.now() - ttlMs;
  const res = db.prepare(`DELETE FROM sesiones WHERE updated_at < ?`).run(cutoff);
  return res.changes;
}
