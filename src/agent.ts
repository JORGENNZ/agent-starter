// Loop de conversación con Claude + tools.
// Procesa un mensaje (texto / imagen / PDF / audio), ejecuta tools si Claude las pide
// y devuelve la respuesta final al caller (típicamente n8n).

import Anthropic from '@anthropic-ai/sdk';
import { SYSTEM_PROMPT } from './lib/prompt';
import { TOOLS } from './tools/definitions';
import { executeTool } from './tools/executor';
import { getSession, saveSession, withLock, repairState } from './lib/memory';
import { downloadMedia } from './lib/media';
import { transcribeAudio } from './lib/whisper';
import { generateTTS, cleanTextForTTS, prepareForAudioNarration } from './lib/tts';
import { uploadMediaToMeta, sendWhatsAppAudio } from './lib/whatsapp_send';

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const MODEL = process.env.CLAUDE_MODEL || 'claude-sonnet-4-20250514';
const MAX_TOOL_ITERATIONS = 8;

// Prompt caching: el system + todas las tools quedan cacheados (5 min).
// Mantén SYSTEM_PROMPT y TOOLS estables para maximizar cache hits.
const SYSTEM_CACHED: Anthropic.Messages.TextBlockParam[] = [
  {
    type: 'text',
    text: SYSTEM_PROMPT,
    cache_control: { type: 'ephemeral' },
  },
];

const TOOLS_CACHED: Anthropic.Messages.Tool[] = TOOLS.map((t, i, arr) =>
  i === arr.length - 1
    ? ({ ...t, cache_control: { type: 'ephemeral' } } as Anthropic.Messages.Tool)
    : t,
);

export interface ProcessInput {
  telefono: string;
  nombre_wa?: string;
  texto: string;
  media_id?: string;
}

export interface ProcessResult {
  reply: string;
}

export async function processMessage(inp: ProcessInput): Promise<ProcessResult> {
  return withLock(inp.telefono, () => processMessageLocked(inp));
}

async function processMessageLocked(inp: ProcessInput): Promise<ProcessResult> {
  const state = getSession(inp.telefono);

  if (repairState(state)) {
    console.log(`[REPAIR] Removed orphan tool_use from state of ${inp.telefono}`);
  }

  let textPrefix = '';
  if (state.messages.length === 0 && inp.nombre_wa) {
    textPrefix = `[CONTEXTO_INTERNO: el cliente se llama ${inp.nombre_wa} en su WhatsApp, no le pidas nombre de nuevo si ya lo sabes. Telefono: ${inp.telefono}]\n\n`;
  }

  let inputWasAudio = false;

  if (inp.media_id) {
    try {
      const media = await downloadMedia(inp.media_id);
      const isImage = media.mime_type.startsWith('image/');
      const isAudio = media.mime_type.startsWith('audio/');
      const isPdf = media.mime_type === 'application/pdf';

      if (isPdf) {
        const textForClaude = inp.texto
          ? `${textPrefix}${inp.texto}`
          : `${textPrefix}[El cliente envió un PDF. Analízalo y resume al cliente lo que entendiste.]`;
        state.messages.push({
          role: 'user',
          content: [
            { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: media.base64 } },
            { type: 'text', text: textForClaude },
          ],
        });
        console.log(`[MEDIA PDF] ${inp.telefono}: ${media.size} bytes`);
      } else if (isImage) {
        const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
        const mediaType = allowedTypes.includes(media.mime_type) ? media.mime_type : 'image/jpeg';
        const textForClaude = inp.texto
          ? `${textPrefix}${inp.texto}`
          : `${textPrefix}[El cliente envió una imagen — descríbela y di al cliente qué entendiste.]`;
        state.messages.push({
          role: 'user',
          content: [
            { type: 'image', source: { type: 'base64', media_type: mediaType as any, data: media.base64 } },
            { type: 'text', text: textForClaude },
          ],
        });
        console.log(`[MEDIA IMG] ${inp.telefono}: ${media.size} bytes ${mediaType}`);
      } else if (isAudio) {
        const audioBuffer = Buffer.from(media.base64, 'base64');
        const transcription = await transcribeAudio(audioBuffer, media.mime_type);
        if (transcription.error || !transcription.text) {
          console.error(`[WHISPER ERROR] ${inp.telefono}: ${transcription.error}`);
          state.messages.push({
            role: 'user',
            content: `${textPrefix}[el cliente mandó una nota de voz pero no se pudo transcribir — pídele que la repita o que escriba el mensaje]`,
          });
        } else {
          console.log(`[WHISPER] ${inp.telefono}: "${transcription.text.substring(0, 120)}"`);
          inputWasAudio = true;
          state.messages.push({
            role: 'user',
            content: `${textPrefix}[Nota de voz del cliente, transcrita literalmente] ${transcription.text}`,
          });
        }
      } else {
        state.messages.push({
          role: 'user',
          content: `${textPrefix}[el cliente envió un archivo (${media.mime_type}) que no puedo procesar. Pídele que lo mande como imagen/audio/PDF o que escriba el mensaje]`,
        });
      }
    } catch (err: any) {
      console.error(`[MEDIA ERROR] ${inp.telefono}:`, err.message);
      state.messages.push({
        role: 'user',
        content: `${textPrefix}${inp.texto || '[error al descargar el archivo. Pide que lo reenvíe o escriba el mensaje.]'}`,
      });
    }
  } else {
    state.messages.push({ role: 'user', content: `${textPrefix}${inp.texto}` });
  }

  if (inputWasAudio) {
    state.datos_cliente.responder_con_audio = true;
  } else if (inp.texto) {
    const lower = inp.texto.toLowerCase();
    if (/conte?sta(me)?\s+(en\s+)?(texto|escrito)/.test(lower) || /mej?or\s+(en\s+)?texto/.test(lower)) {
      state.datos_cliente.responder_con_audio = false;
    } else if (/conte?sta(me)?\s+(en\s+)?audio/.test(lower) || /mej?or\s+(en\s+)?audio/.test(lower) || /mandame?\s+audio/.test(lower)) {
      state.datos_cliente.responder_con_audio = true;
    } else {
      state.datos_cliente.responder_con_audio = false;
    }
  }

  let assistantText = '';
  let iterations = 0;

  while (iterations < MAX_TOOL_ITERATIONS) {
    iterations++;

    const response = await client.messages.create({
      model: MODEL,
      max_tokens: 1024,
      system: SYSTEM_CACHED,
      tools: TOOLS_CACHED,
      messages: state.messages,
    });

    const u: any = response.usage || {};
    if (u.cache_creation_input_tokens || u.cache_read_input_tokens) {
      console.log(`[CACHE] created=${u.cache_creation_input_tokens || 0} read=${u.cache_read_input_tokens || 0} input=${u.input_tokens || 0}`);
    }

    state.messages.push({ role: 'assistant', content: response.content });

    if (response.stop_reason === 'tool_use') {
      const toolResults: Anthropic.Messages.ToolResultBlockParam[] = [];
      for (const block of response.content) {
        if (block.type === 'tool_use') {
          console.log(`[TOOL] ${block.name}`, JSON.stringify(block.input).substring(0, 300));
          const result = await executeTool(block.name, block.input, state, inp.telefono, inp.nombre_wa);
          console.log(`[TOOL RESULT] ${block.name}:`, result.substring(0, 300));
          toolResults.push({
            type: 'tool_result',
            tool_use_id: block.id,
            content: result,
          });
        }
      }
      state.messages.push({ role: 'user', content: toolResults });
      continue;
    }

    for (const block of response.content) {
      if (block.type === 'text') {
        assistantText += block.text;
      }
    }
    break;
  }

  const replyText = assistantText || 'Disculpa, tuve un problema. ¿Puedes repetirme lo último?';

  // Si el reply tiene datos críticos (URL, IDs largos, listas, dinero) mandamos texto sí o sí.
  // Si solo es texto conversacional y el cliente prefiere audio, mandamos audio y suprimimos texto.
  const replyNeedsText = (() => {
    if (/https?:\/\//.test(replyText)) return true;
    if (/[A-Z0-9]{15,}/.test(replyText)) return true;
    const moneyLines = (replyText.match(/\$\s*[\d,\.]+/g) || []).length;
    if (moneyLines >= 2) return true;
    const numberedList = (replyText.match(/^\s*\d+[\.\)\-]/gm) || []).length;
    if (numberedList >= 3) return true;
    if (replyText.length > 500) return true;
    return false;
  })();

  let sendTextToN8n = true;

  if (state.datos_cliente.responder_con_audio && replyText && replyText.length > 3) {
    try {
      const textoParaNarracion = prepareForAudioNarration(replyText);
      const cleaned = cleanTextForTTS(textoParaNarracion);
      const tts = await generateTTS(cleaned);
      if (tts.audio) {
        const uploaded = await uploadMediaToMeta(tts.audio, 'audio/ogg');
        if (uploaded.ok && uploaded.media_id) {
          const sent = await sendWhatsAppAudio(inp.telefono, uploaded.media_id);
          if (sent.ok) {
            console.log(`[TTS] audio enviado a ${inp.telefono} (${tts.audio.length} bytes) | needsText=${replyNeedsText}`);
            if (!replyNeedsText) sendTextToN8n = false;
          } else {
            console.error(`[TTS SEND ERROR] ${sent.error}`);
          }
        } else {
          console.error(`[TTS UPLOAD ERROR] ${uploaded.error}`);
        }
      } else {
        console.error(`[TTS GEN ERROR] ${tts.error}`);
      }
    } catch (err: any) {
      console.error('[TTS FATAL]', err.message);
    }
  }

  saveSession(inp.telefono, state);

  return {
    reply: sendTextToN8n ? replyText : '',
  };
}
