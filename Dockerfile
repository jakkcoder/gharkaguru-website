FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_DISABLE_MSW=true
# Same-origin API via nginx proxy (/v1/api -> FastAPI)
ARG VITE_API_BASE_URL=/v1
ARG VITE_BASE_PATH=/
ENV VITE_DISABLE_MSW=$VITE_DISABLE_MSW
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_BASE_PATH=$VITE_BASE_PATH
RUN npm run build && node scripts/prepare-bucket-deploy.mjs

FROM python:3.12-slim AS runtime

RUN apt-get update \
  && apt-get install -y --no-install-recommends nginx curl \
  && rm -rf /var/lib/apt/lists/* \
  && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/app /app/backend/app
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY scripts/start.sh /app/start.sh
COPY --from=build /app/dist /usr/share/nginx/html

RUN sed -i 's/\r$//' /app/start.sh \
  && chmod +x /app/start.sh \
  && mkdir -p /tmp/website-data \
  && nginx -t

ENV DATA_DIR=/tmp/website-data
ENV PULL_ON_STARTUP=true
ENV PYTHONPATH=/app/backend
ENV PORT=8080

EXPOSE 8080
CMD ["/app/start.sh"]
