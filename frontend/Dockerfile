FROM node:22-slim AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:22-slim AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
COPY --from=deps /app/node_modules ./node_modules
COPY frontend ./
RUN npm run build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
COPY --from=builder /app ./
EXPOSE 3000
CMD ["npm", "run", "start", "--", "-p", "3000"]
