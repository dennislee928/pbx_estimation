FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PBX_WORKSPACE=/workspace \
    HOST=0.0.0.0 \
    PORT=8080

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY services/research_mcp/server.py /app/server.py

EXPOSE 8080

ENTRYPOINT ["python", "/app/server.py"]
CMD ["http"]
