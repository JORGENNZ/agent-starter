// Envía mensajes directos a Meta WhatsApp Cloud API (sin pasar por n8n)
// Útil para: confirmar al cliente cuando admin marca pagado, futuros recordatorios automáticos.

import https from 'https';

const META_TOKEN = process.env.META_ACCESS_TOKEN || '';
const PHONE_NUMBER_ID = process.env.META_PHONE_NUMBER_ID || '';
const GRAPH_VERSION = 'v21.0';

interface SendTextResult {
  ok: boolean;
  error?: string;
  data?: any;
}

function httpsPost(hostname: string, path: string, token: string, body: any): Promise<{ statusCode: number; data: string }> {
  return new Promise((resolve, reject) => {
    const payload = Buffer.from(JSON.stringify(body), 'utf8');
    const req = https.request({
      hostname,
      path,
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Content-Length': String(payload.length),
      },
    }, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => resolve({ statusCode: res.statusCode || 0, data }));
    });
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

/** Manda un mensaje de texto a un número de WhatsApp. Requiere que el receptor haya escrito en las últimas 24h. */
export async function sendWhatsAppText(to: string, text: string): Promise<SendTextResult> {
  if (!META_TOKEN || !PHONE_NUMBER_ID) {
    return { ok: false, error: 'META_ACCESS_TOKEN o META_PHONE_NUMBER_ID faltantes en .env' };
  }
  const body = {
    messaging_product: 'whatsapp',
    recipient_type: 'individual',
    to,
    type: 'text',
    text: { body: text },
  };
  const res = await httpsPost('graph.facebook.com', `/${GRAPH_VERSION}/${PHONE_NUMBER_ID}/messages`, META_TOKEN, body);
  if (res.statusCode >= 200 && res.statusCode < 300) {
    return { ok: true, data: JSON.parse(res.data) };
  }
  return { ok: false, error: `HTTP ${res.statusCode}: ${res.data.substring(0, 300)}` };
}

/** Sube media (audio, imagen, etc.) a Meta. Devuelve media_id reutilizable para mandar mensajes. */
export async function uploadMediaToMeta(buffer: Buffer, mimeType: string): Promise<{ ok: boolean; media_id?: string; error?: string }> {
  if (!META_TOKEN || !PHONE_NUMBER_ID) {
    return { ok: false, error: 'META_ACCESS_TOKEN o META_PHONE_NUMBER_ID faltantes' };
  }

  const extFromMime = mimeType.includes('ogg') ? 'ogg'
                    : mimeType.includes('mp3') || mimeType.includes('mpeg') ? 'mp3'
                    : mimeType.includes('aac') ? 'aac'
                    : mimeType.includes('m4a') || mimeType.includes('mp4') ? 'm4a'
                    : 'bin';

  const form = new FormData();
  form.append('messaging_product', 'whatsapp');
  form.append('file', new Blob([new Uint8Array(buffer)], { type: mimeType }), `audio.${extFromMime}`);
  form.append('type', mimeType);

  try {
    const res = await fetch(`https://graph.facebook.com/${GRAPH_VERSION}/${PHONE_NUMBER_ID}/media`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${META_TOKEN}` },
      body: form as any,
    });
    if (!res.ok) {
      const errText = await res.text();
      return { ok: false, error: `Upload HTTP ${res.status}: ${errText.substring(0, 200)}` };
    }
    const data = (await res.json()) as { id: string };
    return { ok: true, media_id: data.id };
  } catch (err: any) {
    return { ok: false, error: `Upload error: ${err.message}` };
  }
}

/** Manda un mensaje tipo audio al cliente usando un media_id previamente subido. */
export async function sendWhatsAppAudio(to: string, mediaId: string): Promise<SendTextResult> {
  if (!META_TOKEN || !PHONE_NUMBER_ID) {
    return { ok: false, error: 'META_ACCESS_TOKEN o META_PHONE_NUMBER_ID faltantes' };
  }
  const body = {
    messaging_product: 'whatsapp',
    recipient_type: 'individual',
    to,
    type: 'audio',
    audio: { id: mediaId },
  };
  const res = await httpsPost('graph.facebook.com', `/${GRAPH_VERSION}/${PHONE_NUMBER_ID}/messages`, META_TOKEN, body);
  if (res.statusCode >= 200 && res.statusCode < 300) {
    return { ok: true, data: JSON.parse(res.data) };
  }
  return { ok: false, error: `HTTP ${res.statusCode}: ${res.data.substring(0, 300)}` };
}
