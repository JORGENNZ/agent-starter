# agent-starter

Starter de **agente conversacional para WhatsApp** con Claude (tool use + prompt caching) y n8n como puente.

Soporta entrada de **texto, imagen, PDF y audio** (Whisper) y puede responder con **TTS** (OpenAI) como nota de voz nativa.

> Este template se construyó extrayendo el esqueleto de un agente de producción y quitando toda la lógica de dominio. Cambia el system prompt + las tools y tienes un agente para tu propio caso de uso.

## Estructura

```
Dockerfile           — multi-stage build (Node 20 + better-sqlite3 nativo)
docker-compose.yml   — agente + n8n en misma red, listo para `docker compose up`
.env.example         — variables de entorno
src/
  index.ts           — Express: /message, /reset, /health, /admin/conversaciones
  agent.ts           — Loop conversación con Claude (tool use, prompt caching, multimodal)
  lib/
    prompt.ts        — System prompt — REEMPLAZAR con tu dominio
    memory.ts        — Sesiones por teléfono (RAM + SQLite, locks, dedup)
    db.ts            — SQLite (solo tabla `sesiones`)
    media.ts         — Descarga imágenes/PDF/audio de Meta
    whisper.ts       — Transcripción de notas de voz (OpenAI)
    tts.ts           — Text-to-Speech (OpenAI, OGG/Opus)
    whatsapp_send.ts — Envío directo a Meta (texto + audio)
  tools/
    definitions.ts   — Schemas de las tools — REEMPLAZAR con tus tools
    executor.ts      — Implementación de las tools — REEMPLAZAR
```

## Setup local (sin Docker)

```bash
npm install
cp .env.example .env
# editar .env con tus keys
npm run dev
```

## Setup con Docker (recomendado para VPS)

Levanta **agente + n8n** en la misma red de un solo golpe:

```bash
cp .env.example .env
# editar .env con tus keys
docker compose up -d
```

- n8n queda en `http://<tu-vps>:5678` (UI web)
- El agente NO expone puerto al exterior por defecto (más seguro). n8n lo llama internamente vía `http://agent:3000/message`.
- Si necesitas que el agente reciba webhooks externos directamente, descomenta el bloque `ports:` del servicio `agent` en `docker-compose.yml`.

Comandos útiles:
```bash
docker compose logs -f agent     # logs del agente
docker compose logs -f n8n       # logs de n8n
docker compose restart agent     # reiniciar tras cambio de .env
docker compose build agent       # rebuild tras cambio de código
docker compose down              # apagar todo (los datos quedan en los volúmenes)
```

Para actualizar el agente tras un cambio de código:
```bash
git pull
docker compose build agent && docker compose up -d agent
```

Los datos persisten en volúmenes Docker:
- `agent_data` → `agent.db` (sesiones de conversación)
- `n8n_data` → workflows y credenciales de n8n

## Cómo adaptarlo a TU caso de uso

Solo tocas **3 archivos**:

### 1. `src/lib/prompt.ts` — quién es y qué hace tu agente
Reemplaza el placeholder por la persona, objetivo, flujo y reglas duras. Mantén el string **estable** (no varíes saludos por usuario aquí — eso va como user message) para que el prompt caching haga hit.

### 2. `src/tools/definitions.ts` — qué tools puede invocar
Define las tools como `Anthropic.Messages.Tool[]`. Cada una con:
- `name`: identificador
- `description`: cuándo debe usarla el modelo
- `input_schema`: JSON Schema de parámetros

### 3. `src/tools/executor.ts` — qué hace cada tool al ejecutarse
Switch por `name` → llama tu API/lógica → devuelve string (idealmente JSON). El resultado se reinyecta en la conversación automáticamente.

Las tools tienen acceso al `state` de sesión (puedes guardar datos del cliente en `state.datos_cliente`) y al `telefono` del cliente.

## Endpoints

### `POST /message` — entrada principal (lo llama n8n)
```json
{
  "telefono": "5215555555555",
  "nombre_wa": "Juan",
  "texto": "Hola, necesito ayuda",
  "media_id": "1234567890123456",
  "wa_message_id": "wamid.XXX"
}
```
Respuesta:
```json
{ "reply": "¡Hola Juan! ¿En qué te ayudo?" }
```
- `texto` o `media_id` son requeridos; los demás son opcionales.
- Si `media_id` viene, se descarga de Meta y se procesa según el mime type (imagen → visión, PDF → documento, audio → Whisper).
- Si el cliente mandó audio, el agente puede responder con audio (TTS) y dejar el `reply` vacío para que n8n no mande también el texto.

### `POST /reset` — borra la sesión de un teléfono
```json
{ "telefono": "5215555555555" }
```

### `GET /health`
```json
{ "ok": true }
```

### `GET /admin/conversaciones` (Basic Auth)
Listado de las últimas 50 conversaciones con preview. Útil para debuggear.

### `GET /admin/conversaciones/:telefono`
Conversación completa del teléfono (incluye tool uses / tool results).

## Integración con n8n (WhatsApp Cloud API)

Workflow típico de 4 nodos en n8n:

1. **Webhook** — recibe el POST de Meta (verify GET + receive POST)
2. **Code/Set** — extrae `telefono`, `nombre_wa`, `texto`, `media_id`, `wa_message_id` del payload de Meta
3. **HTTP Request** — `POST http://<host>:3000/message` con esos campos
4. **HTTP Request** — manda la respuesta a `https://graph.facebook.com/v21.0/<PHONE_ID>/messages` (texto)

Si quieres soporte de PDF/audio:
- El agente ya descarga el media y procesa todo internamente — n8n solo pasa `media_id`.
- Si el agente responde con audio (cuando el cliente manda audio), lo envía **directo a Meta** vía `whatsapp_send.ts` (n8n no se entera). El `reply` del response vendrá vacío y n8n debe saltarse el envío de texto en ese caso.

## Despliegue (VPS Hostinger u otro)

**Opción A — Docker Compose (recomendado, lleva n8n incluido):**
```bash
git clone <tu-repo> && cd agent-starter
cp .env.example .env && nano .env
docker compose up -d
```
Eso es todo. n8n queda en `:5678`, el agente arranca al boot (restart: unless-stopped).

**Opción B — Node directo con PM2 (si ya tienes n8n corriendo aparte):**
```bash
npm install
npm run build
pm2 start dist/index.js --name agent
pm2 save && pm2 startup
```

En ambos casos la DB SQLite persiste y las conversaciones sobreviven reinicios (TTL 7 días).

## Notas técnicas

- **Modelo**: por defecto `claude-sonnet-4-20250514` (override con `CLAUDE_MODEL` en `.env`).
- **Prompt caching**: el system prompt + todas las tools están marcadas con `cache_control: ephemeral`. Se paga 10% del costo en cache reads (5 min TTL). Mantén `SYSTEM_PROMPT` y `TOOLS` lo más estables posible.
- **Lock por teléfono**: si llegan 2 mensajes seguidos del mismo cliente, se procesan secuencialmente (evita corromper la conversación).
- **Auto-repair**: si un crash dejó un `tool_use` huérfano en la sesión, lo limpia al siguiente mensaje en vez de tirar 400.
- **Dedup Meta**: si Meta reintenta el mismo webhook con el mismo `wa_message_id`, se ignora (5 min TTL).
