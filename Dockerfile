FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3003

WORKDIR /app

RUN groupadd --system souls \
 && useradd --system --gid souls --create-home souls

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY app.py zones.py logo.JPG ./
COPY templates/ templates/
COPY static/ static/

RUN chown -R souls:souls /app
USER souls

EXPOSE 3003

CMD ["gunicorn", "--bind", "0.0.0.0:3003", "--workers", "1", "--threads", "4", "--timeout", "60", "app:app"]
