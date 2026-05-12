# Multi-stage build: compilamos TypeScript + better-sqlite3 nativo en la stage "build",
# y la imagen final solo lleva node_modules de producción + dist/.
# Resultado: ~150MB en vez de ~500MB.

# ─── Stage 1: build ─────────────────────────────────────────
FROM node:20-bookworm-slim AS build

# Herramientas para compilar better-sqlite3 (node-gyp, python3, gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 make g++ \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# Reinstalamos solo dependencias de producción (descarta tsx, @types, typescript)
RUN npm prune --omit=dev

# ─── Stage 2: runtime ───────────────────────────────────────
FROM node:20-bookworm-slim AS runtime

WORKDIR /app
ENV NODE_ENV=production

# Copiamos solo lo necesario para correr
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./

# Carpeta para la DB SQLite (montar como volumen)
RUN mkdir -p /data && chown node:node /data
USER node
ENV DB_PATH=/data/agent.db

EXPOSE 3000

CMD ["node", "dist/index.js"]
