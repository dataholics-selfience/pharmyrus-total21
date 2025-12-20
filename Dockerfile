# Dockerfile PRODUCTION - Railway Compatible
FROM ubuntu:22.04

# Evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Definir diretório de trabalho
WORKDIR /app

# Instalar Python 3.10 e dependências do sistema
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Criar symlinks para python
RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/python3.10 /usr/bin/python3

# Copiar requirements primeiro (cache layer)
COPY requirements.txt .

# Instalar dependências Python
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Instalar Playwright e Chromium
RUN playwright install chromium

# Instalar dependências do Playwright manualmente
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    fonts-liberation \
    fonts-noto-color-emoji \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copiar código da aplicação
COPY app/ ./app/
COPY api_deploy.py .

# Expor porta padrão (Railway usa $PORT dinâmico)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:${PORT:-8000}/health', timeout=5)" || exit 1

# Comando de inicialização (shell form para expansão de variáveis)
# Railway define $PORT automaticamente, usa 8000 como fallback
CMD uvicorn api_deploy:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
