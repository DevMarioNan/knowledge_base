FROM node:22-alpine AS builder

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

COPY . .
ARG VITE_API_BASE_URL=/api
RUN VITE_API_BASE_URL=${VITE_API_BASE_URL} pnpm build

FROM nginx:alpine

RUN apk add --no-cache curl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -sf http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
