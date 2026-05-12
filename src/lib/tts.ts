// Text-to-Speech con OpenAI TTS
// Genera OGG/Opus (para que WhatsApp lo muestre como nota de voz visual)

const OPENAI_KEY = process.env.OPENAI_API_KEY || '';
const TTS_URL = 'https://api.openai.com/v1/audio/speech';
const TTS_VOICE = process.env.TTS_VOICE || 'onyx'; // onyx=grave asesor, echo=joven, alloy=neutral, nova=femenina
const TTS_MODEL = process.env.TTS_MODEL || 'tts-1'; // tts-1=rápido/barato, tts-1-hd=mejor calidad

export interface TTSResult {
  audio?: Buffer;
  mime_type?: string;
  error?: string;
}

/** Genera audio OGG/Opus a partir de texto. Ideal para WhatsApp (lo muestra como voice note). */
export async function generateTTS(text: string): Promise<TTSResult> {
  if (!OPENAI_KEY) return { error: 'OPENAI_API_KEY no configurado' };
  if (!text || !text.trim()) return { error: 'texto vacío' };

  try {
    const res = await fetch(TTS_URL, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${OPENAI_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: TTS_MODEL,
        input: text,
        voice: TTS_VOICE,
        response_format: 'opus', // WhatsApp voice note-compatible
      }),
    });
    if (!res.ok) {
      const err = await res.text();
      return { error: `TTS HTTP ${res.status}: ${err.substring(0, 200)}` };
    }
    const arrayBuf = await res.arrayBuffer();
    return {
      audio: Buffer.from(arrayBuf),
      mime_type: 'audio/ogg; codecs=opus',
    };
  } catch (err: any) {
    return { error: `TTS error: ${err.message}` };
  }
}

/** Limpia texto antes de TTS: quita markdown, emojis redundantes, y URLs largas (que suenan feo). */
export function cleanTextForTTS(text: string): string {
  return text
    .replace(/\*(.+?)\*/g, '$1')                       // quita * de negrita (Claude los usa)
    .replace(/_(.+?)_/g, '$1')                         // quita _ cursiva
    .replace(/`(.+?)`/g, '$1')                         // quita backticks
    .replace(/https?:\/\/\S+/g, 'el link que te paso por texto')
    .replace(/\n{2,}/g, '. ')                          // doble salto → pausa
    .replace(/\n/g, ' ')                               // salto simple → espacio
    .trim();
}

/**
 * Convierte el texto completo en una narración breve para TTS cuando hay contenido
 * que suena feo leído (listas numeradas, varios precios, URLs largas).
 * El TEXTO original sigue yendo completo al cliente; solo el AUDIO se resume.
 */
export function prepareForAudioNarration(fullText: string): string {
  const numberedList = (fullText.match(/^\s*\d+[\.\)\-]/gm) || []).length;
  const moneyLines = (fullText.match(/\$\s*[\d,\.]+/g) || []).length;

  // Lista numerada larga (códigos, opciones) — suena feo leída
  if (numberedList >= 3 && moneyLines < 2) {
    return `Te mando las opciones abajo por texto. Revísalas y dime cuál te interesa.`;
  }

  // Lista de precios (3+ precios)
  if (moneyLines >= 3) {
    return `Ya te traje las opciones con sus precios. Revísalas en el mensaje de texto y dime con cuál avanzamos.`;
  }

  // Respuesta con URLs largas
  if (/https?:\/\//.test(fullText) && fullText.length > 250) {
    const firstSentence = fullText.split(/[.\n]/)[0] || '';
    return `${firstSentence}. Te mando los detalles completos por texto.`;
  }

  return fullText;
}
