// Memoria de conversaciones por cliente (teléfono).
// Persistencia híbrida: RAM cache (rápido) + SQLite (sobrevive reinicios).

import Anthropic from '@anthropic-ai/sdk';
import { dbGetSesion, dbSaveSesion, dbDeleteSesion, dbCleanExpiredSesiones } from './db';

export interface ConversationState {
  messages: Anthropic.Messages.MessageParam[];
  datos_cliente: Record<string, any>; // datos acumulados del cliente
  extras?: any; // estado de dominio libre (lo que necesites)
  updatedAt: number;
}

const TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 días (con DB persistente podemos darle ventana larga)
const ramCache = new Map<string, ConversationState>();

export function getSession(telefono: string): ConversationState {
  // 1. Intentar RAM cache (rápido)
  const cached = ramCache.get(telefono);
  if (cached) return cached;

  // 2. Intentar SQLite (sesión que sobrevivió reinicios)
  const fromDB = dbGetSesion(telefono);
  if (fromDB) {
    if (Date.now() - fromDB.updatedAt > TTL_MS) {
      dbDeleteSesion(telefono);
    } else {
      const state: ConversationState = {
        messages: fromDB.messages as Anthropic.Messages.MessageParam[],
        datos_cliente: fromDB.datos_cliente,
        extras: fromDB.extras,
        updatedAt: fromDB.updatedAt,
      };
      ramCache.set(telefono, state);
      console.log(`[SESION] cargada de DB para ${telefono} (${state.messages.length} mensajes)`);
      return state;
    }
  }

  // 3. Nueva sesión
  const fresh: ConversationState = { messages: [], datos_cliente: {}, updatedAt: Date.now() };
  ramCache.set(telefono, fresh);
  return fresh;
}

export function saveSession(telefono: string, state: ConversationState) {
  state.updatedAt = Date.now();
  ramCache.set(telefono, state);
  // Escribir a DB (better-sqlite3 es síncrono y muy rápido)
  dbSaveSesion(telefono, {
    messages: state.messages,
    datos_cliente: state.datos_cliente,
    extras: state.extras,
    updatedAt: state.updatedAt,
  });
}

export function resetSession(telefono: string) {
  ramCache.delete(telefono);
  dbDeleteSesion(telefono);
  locks.delete(telefono);
}

// ----- Deduplicación de mensajes de WhatsApp (Meta a veces entrega 2x el mismo webhook) -----
const processedMessages = new Map<string, number>();
const DEDUP_TTL_MS = 5 * 60 * 1000; // 5 min

export function isDuplicate(messageId: string): boolean {
  if (!messageId) return false;
  const now = Date.now();
  for (const [k, t] of processedMessages.entries()) {
    if (now - t > DEDUP_TTL_MS) processedMessages.delete(k);
  }
  if (processedMessages.has(messageId)) return true;
  processedMessages.set(messageId, now);
  return false;
}

// Limpieza periódica de sesiones expiradas (cada 1 hora)
setInterval(() => {
  try {
    const deleted = dbCleanExpiredSesiones(TTL_MS);
    if (deleted > 0) console.log(`[CLEAN] ${deleted} sesiones expiradas borradas de DB`);
    const now = Date.now();
    for (const [k, v] of ramCache.entries()) {
      if (now - v.updatedAt > TTL_MS) {
        ramCache.delete(k);
        locks.delete(k);
      }
    }
  } catch (err: any) {
    console.error('[CLEAN ERROR]', err.message);
  }
}, 60 * 60 * 1000);

// ----- Locks por teléfono (evita race conditions con mensajes concurrentes) -----
const locks = new Map<string, Promise<void>>();

export async function withLock<T>(telefono: string, fn: () => Promise<T>): Promise<T> {
  const prev = locks.get(telefono) || Promise.resolve();
  let release!: () => void;
  const current = new Promise<void>((resolve) => { release = resolve; });
  const chained = prev.then(() => current);
  locks.set(telefono, chained);
  await prev;
  try {
    return await fn();
  } finally {
    release();
    if (locks.get(telefono) === chained) {
      locks.delete(telefono);
    }
  }
}

// Repara state si el último mensaje es assistant con tool_use sin tool_result.
// Quita el turno corrupto para que Claude pueda continuar sin 400.
export function repairState(state: ConversationState): boolean {
  if (state.messages.length === 0) return false;
  const last = state.messages[state.messages.length - 1];
  if (last.role !== 'assistant') return false;
  const content = last.content;
  if (!Array.isArray(content)) return false;
  const hasToolUse = content.some((b: any) => b.type === 'tool_use');
  if (!hasToolUse) return false;
  state.messages.pop(); // assistant con tool_use huérfano
  if (state.messages.length > 0) {
    const prev = state.messages[state.messages.length - 1];
    if (prev.role === 'user' && typeof prev.content === 'string') {
      state.messages.pop();
    }
  }
  return true;
}
