FROM node:22-alpine AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY frontend ./frontend
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY data/Onelab_Reconciliation_Data.xlsx ./data/Onelab_Reconciliation_Data.xlsx
COPY --from=frontend /app/web-build ./web-build
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
