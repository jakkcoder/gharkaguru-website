FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_DISABLE_MSW=true
ARG VITE_API_BASE_URL=https://api.gharkaguru.com/v1
ARG VITE_BASE_PATH=/
ENV VITE_DISABLE_MSW=$VITE_DISABLE_MSW
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_BASE_PATH=$VITE_BASE_PATH
RUN npm run build && node scripts/prepare-bucket-deploy.mjs

FROM nginx:alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

