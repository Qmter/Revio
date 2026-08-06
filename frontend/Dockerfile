# --- ЭТАП 1: Сборка React приложения ---
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# --- ЭТАП 2: Запуск легкого Nginx сервера ---
FROM nginx:alpine

# Копируем собранный статический бандл в папку Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Копируем наш конфиг Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]