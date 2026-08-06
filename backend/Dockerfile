FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# Используем надежное глобальное зеркало с отключенным жестким SSL-дропом
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --default-timeout=120 \
    -r requirements.txt

COPY . .

CMD ["uvicorn", "services.webhook_ingestion.main:app", "--host", "0.0.0.0", "--port", "8000"]