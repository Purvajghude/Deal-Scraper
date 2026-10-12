FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hermes/ hermes/
COPY profile.yaml .

ENV HERMES_DB=/data/hermes.db
ENV HOST=0.0.0.0
ENV HERMES_PUBLIC_READ_ONLY=1
RUN mkdir -p /data
VOLUME /data
EXPOSE 8787

CMD ["python", "-m", "hermes", "serve"]
