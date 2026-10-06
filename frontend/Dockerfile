FROM node:22-alpine
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
ENV WM_BACKEND_URL=http://backend:8000
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
