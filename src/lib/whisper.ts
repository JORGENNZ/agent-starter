// Transcripción de audios con OpenAI Whisper API
// WhatsApp manda notas de voz en OGG/Opus — Whisper las acepta sin conversión.

const OPENAI_KEY = process.env.OPENAI_API_KEY || '';
const WHISPER_URL = 'https://api.openai.com/v1/audio/transcriptions';

export interface TranscriptionResult {
  text: string;
  error?: string;
  duration_sec?: number;
}

/** Transcribe un audio (Buffer) usando Whisper. Idioma forzado a español para mejor precisión. */
export async function transcribeAudio(audioBuffer: Buffer, mimeType: string): Promise<TranscriptionResult> {
  if (!OPENAI_KEY) {
    return { text: '', error: 'OPENAI_API_KEY no configurado en .env' };
  }

  // Determinar extensión según mime_type (Whisper requiere filename con extensión válida)
  const ext = mimeType.includes('ogg') ? 'ogg'
            : mimeType.includes('mp3') || mimeType.includes('mpeg') ? 'mp3'
            : mimeType.includes('wav') ? 'wav'
            : mimeType.includes('m4a') || mimeType.includes('mp4') ? 'm4a'
            : mimeType.includes('webm') ? 'webm'
            : 'ogg';

  const form = new FormData();
  const blob = new Blob([new Uint8Array(audioBuffer)], { type: mimeType });
  form.append('file', blob, `audio.${ext}`);
  form.append('model', 'whisper-1');
  form.append('language', 'es');
  form.append('response_format', 'json');

  try {
    const res = await fetch(WHISPER_URL, {
      method: 'POST',
      headers: { Authorization: `Bearer ${OPENAI_KEY}` },
      body: form as any,
    });
    if (!res.ok) {
      const errText = await res.text();
      return { text: '', error: `Whisper HTTP ${res.status}: ${errText.substring(0, 200)}` };
    }
    const data = (await res.json()) as { text: string };
    return { text: (data.text || '').trim() };
  } catch (err: any) {
    return { text: '', error: `Whisper error: ${err.message}` };
  }
}
