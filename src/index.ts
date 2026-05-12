// Servidor HTTP que expone /message para que n8n (u otro caller) lo llame.

import 'dotenv/config';
import express from 'express';
import { processMessage } from './agent';
import { resetSession, isDuplicate } from './lib/memory';
import { dbListSesiones, dbGetConversacion, dbDeleteSesion } from './lib/db';

const app = express();
app.use(express.json({ limit: '2mb' }));

const PORT = Number(process.env.PORT || 3000);

app.get('/health', (_req, res) => res.json({ ok: true }));

// ─────────────────────────────────────────────────────────────
// Endpoint principal: lo llama n8n con el mensaje entrante de WhatsApp.
// Body esperado: { telefono, nombre_wa?, texto, media_id?, wa_message_id? }
// ─────────────────────────────────────────────────────────────
app.post('/message', async (req, res) => {
  try {
    const { telefono, nombre_wa, texto, media_id, wa_message_id } = req.body;
    if (!telefono || (!texto && !media_id)) {
      return res.status(400).json({ error: 'Faltan campos: telefono + (texto o media_id)' });
    }

    // Dedup: Meta a veces reintenta el mismo webhook
    if (wa_message_id && isDuplicate(wa_message_id)) {
      console.log(`[DEDUP] ${telefono}: ${wa_message_id} ya procesado, skip`);
      return res.json({ reply: '', skipped: true });
    }

    const tag = media_id ? `[MEDIA ${media_id.substring(0, 12)}…]` : (texto || '').substring(0, 100);
    console.log(`[IN] ${telefono}: ${tag}`);

    const result = await processMessage({ telefono, nombre_wa, texto: texto || '', media_id });
    console.log(`[OUT] ${telefono}: ${result.reply.substring(0, 100)}`);
    res.json(result);
  } catch (err: any) {
    console.error('[ERROR]', err);
    res.status(500).json({
      error: String(err.message || err),
      reply: 'Disculpa, tuve un problema técnico. Intenta en unos minutos.',
    });
  }
});

app.post('/reset', (req, res) => {
  const { telefono } = req.body;
  if (telefono) resetSession(telefono);
  res.json({ ok: true });
});

// ─────────────────────────────────────────────────────────────
// Inspector de conversaciones (Basic Auth) — para debug
// ─────────────────────────────────────────────────────────────
const ADMIN_USER = process.env.ADMIN_USER || '';
const ADMIN_PASS = process.env.ADMIN_PASS || '';

function requireAuth(req: express.Request, res: express.Response, next: express.NextFunction) {
  if (!ADMIN_USER || !ADMIN_PASS) {
    return res.status(503).send('Admin no configurado (define ADMIN_USER y ADMIN_PASS en .env)');
  }
  const auth = req.headers.authorization || '';
  if (!auth.startsWith('Basic ')) {
    res.setHeader('WWW-Authenticate', 'Basic realm="Agent Admin"');
    return res.status(401).send('Auth required');
  }
  const [user, pass] = Buffer.from(auth.slice(6), 'base64').toString('utf8').split(':');
  if (user !== ADMIN_USER || pass !== ADMIN_PASS) {
    res.setHeader('WWW-Authenticate', 'Basic realm="Agent Admin"');
    return res.status(401).send('Auth invalid');
  }
  next();
}

app.get('/admin/conversaciones', requireAuth, (_req, res) => {
  res.json(dbListSesiones(50));
});

app.get('/admin/conversaciones/:telefono', requireAuth, (req, res) => {
  const conv = dbGetConversacion(req.params.telefono);
  if (!conv) return res.status(404).json({ error: 'No encontrada' });
  res.json(conv);
});

app.delete('/admin/conversaciones/:telefono', requireAuth, (req, res) => {
  dbDeleteSesion(req.params.telefono);
  res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`Agent escuchando en :${PORT}`);
});
