// Ejecutor genérico de tools.
// El loop en src/agent.ts llama a executeTool() por cada bloque tool_use que devuelve Claude
// y reinyecta el resultado en la conversación.
//
// Reemplaza la lógica de cada `case` por la implementación real de tu dominio.

import { ConversationState } from '../lib/memory';

export async function executeTool(
  name: string,
  input: any,
  state: ConversationState,
  telefono: string,
  _nombreWa?: string,
): Promise<string> {
  try {
    switch (name) {
      case 'guardar_dato_cliente': {
        const { campo, valor } = input || {};
        if (!campo || typeof valor === 'undefined') {
          return JSON.stringify({ error: 'Faltan "campo" o "valor"' });
        }
        state.datos_cliente[campo] = valor;
        return JSON.stringify({ ok: true, campo, valor });
      }

      case 'consultar_backend': {
        // TODO: reemplaza por la llamada real a tu API.
        // Ejemplo:
        //   const r = await fetch(`${process.env.BACKEND_URL}/...`, { ... });
        //   const data = await r.json();
        //   return JSON.stringify(data);
        const { accion, parametros } = input || {};
        return JSON.stringify({
          ok: true,
          stub: true,
          mensaje:
            'Tool stub — implementa la llamada real a tu backend en src/tools/executor.ts',
          accion,
          parametros,
        });
      }

      default:
        return JSON.stringify({ error: `Tool desconocido: ${name}` });
    }
  } catch (err: any) {
    console.error(`[TOOL ${name}] error para ${telefono}:`, err.message);
    return JSON.stringify({ error: err.message || String(err) });
  }
}
