FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml .

# Используем надежное глобальное зеркало с отключенным жестким SSL-дропом
RUN pip install --no-cache-dir --no-build-isolation \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --default-timeout=120 \
    .
    
COPY . .

CMD ["uvicorn", "services.webhook_ingestion.main:app", "--host", "0.0.0.0", "--port", "8000"]