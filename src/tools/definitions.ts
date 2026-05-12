// Define aquí las tools que tu agente puede invocar.
// El loop en src/agent.ts se encarga de ejecutar y reinyectar los resultados.
//
// Cada tool sigue el formato Anthropic Tool Use:
//   - name: identificador estable
//   - description: explica QUÉ hace y CUÁNDO debe usarla el modelo
//   - input_schema: JSON Schema de los parámetros
//
// Reemplaza estos ejemplos por las tools de tu dominio.

import Anthropic from '@anthropic-ai/sdk';

export const TOOLS: Anthropic.Messages.Tool[] = [
  {
    name: 'guardar_dato_cliente',
    description:
      'Guarda un dato del cliente en la sesión (nombre, email, preferencia, etc.) ' +
      'para usarlo después sin volver a preguntarlo. Úsala apenas el cliente lo mencione.',
    input_schema: {
      type: 'object',
      properties: {
        campo: { type: 'string', description: 'Nombre del campo (ej. "nombre", "email", "ciudad")' },
        valor: { type: 'string', description: 'Valor a guardar' },
      },
      required: ['campo', 'valor'],
    },
  },
  {
    name: 'consultar_backend',
    description:
      'Ejecuta una consulta contra tu backend/API de dominio (precios, disponibilidad, status de un ' +
      'pedido, lo que aplique). Devuelve el resultado en texto/JSON para que el agente lo use al responder.',
    input_schema: {
      type: 'object',
      properties: {
        accion: {
          type: 'string',
          description: 'Qué quieres consultar — ej. "precio", "disponibilidad", "status_pedido"',
        },
        parametros: {
          type: 'object',
          description: 'Parámetros de la consulta (objeto libre, depende de tu API)',
          additionalProperties: true,
        },
      },
      required: ['accion'],
    },
  },
];
