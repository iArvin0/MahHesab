FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MAHHESAB_CONTAINER=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 mahhesab \
    && useradd --uid 10001 --gid 10001 --no-create-home mahhesab \
    && install -d -o mahhesab -g mahhesab /data

COPY bot.py finance.py ./
USER mahhesab
CMD ["python", "bot.py"]
