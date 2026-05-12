// Descarga de imágenes desde Meta WhatsApp Graph API

import https from 'https';

const META_TOKEN = process.env.META_ACCESS_TOKEN || '';
const GRAPH_VERSION = 'v21.0';

export interface DownloadedMedia {
  base64: string;
  mime_type: string;
  size: number;
}

function httpsGet(hostname: string, path: string, auth: string): Promise<{ data: Buffer; headers: any; statusCode: number }> {
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname,
      path,
      method: 'GET',
      headers: { Authorization: `Bearer ${auth}`, 'User-Agent': 'agent-starter/1.0' },
    }, (res) => {
      const chunks: Buffer[] = [];
      res.on('data', (c) => chunks.push(Buffer.isBuffer(c) ? c : Buffer.from(c)));
      res.on('end', () => resolve({
        data: Buffer.concat(chunks),
        headers: res.headers,
        statusCode: res.statusCode || 0,
      }));
    });
    req.on('error', reject);
    req.end();
  });
}

/** Descarga una imagen de WhatsApp dado su media_id. Las URLs expiran a los 5 min. */
export async function downloadMedia(mediaId: string): Promise<DownloadedMedia> {
  if (!META_TOKEN) throw new Error('META_ACCESS_TOKEN no configurado en .env');

  // 1. Obtener la URL de descarga
  const meta = await httpsGet('graph.facebook.com', `/${GRAPH_VERSION}/${mediaId}`, META_TOKEN);
  if (meta.statusCode !== 200) {
    throw new Error(`Meta media lookup failed ${meta.statusCode}: ${meta.data.toString().substring(0, 200)}`);
  }
  const info = JSON.parse(meta.data.toString());
  if (!info.url) throw new Error(`Meta media sin URL: ${JSON.stringify(info).substring(0, 200)}`);

  // 2. Descargar el binario (la URL de Meta va a lookaside.fbsbx.com u otro CDN)
  const parsed = new URL(info.url);
  const bin = await httpsGet(parsed.hostname, parsed.pathname + parsed.search, META_TOKEN);
  if (bin.statusCode !== 200) {
    throw new Error(`Media download failed ${bin.statusCode}`);
  }

  return {
    base64: bin.data.toString('base64'),
    mime_type: info.mime_type || 'image/jpeg',
    size: bin.data.length,
  };
}
