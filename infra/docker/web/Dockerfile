FROM node:22-alpine AS deps

WORKDIR /app

COPY apps/web/package.json apps/web/pnpm-lock.yaml ./

RUN npm install -g pnpm && pnpm install --frozen-lockfile

FROM node:22-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
COPY apps/web/next.config.mjs apps/web/next-env.d.ts apps/web/tsconfig.json apps/web/postcss.config.mjs apps/web/components.json ./
COPY apps/web/app ./app
COPY apps/web/components ./components
COPY apps/web/hooks ./hooks
COPY apps/web/lib ./lib
COPY apps/web/public ./public
COPY apps/web/styles ./styles

RUN npm install -g pnpm && pnpm run build

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/next.config.mjs ./next.config.mjs

EXPOSE 3000

RUN npm install -g pnpm
CMD ["pnpm", "start"]
