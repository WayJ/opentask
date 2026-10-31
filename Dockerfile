# Backend Dockerfile
FROM node:20-alpine AS builder

WORKDIR /workspace

COPY package*.json ./
COPY prisma ./prisma/
RUN npm ci

COPY . .
RUN npx prisma generate
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /workspace

COPY --from=builder /workspace/dist ./dist
COPY --from=builder /workspace/node_modules ./node_modules
COPY --from=builder /workspace/package*.json ./
COPY --from=builder /workspace/prisma ./prisma

RUN npx prisma generate

EXPOSE 3000

CMD ["npm", "run", "start:prod"]
