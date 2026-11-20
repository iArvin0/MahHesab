FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KHARJBAN_DB=/data/kharjban.sqlite3

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 kharjban \
    && useradd --uid 10001 --gid 10001 --no-create-home kharjban \
    && install -d -o kharjban -g kharjban /data

COPY bot.py finance.py ./
USER kharjban
CMD ["python", "bot.py"]
