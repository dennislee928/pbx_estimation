FROM node:22-slim

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=7860
ENV HOST=0.0.0.0
ENV RAG_ASSET_PREFIX=latest
ENV HF_RAG_ASSET_ROOT=/app/dist/hf_assets

COPY package.json ./
COPY src ./src
COPY dist ./dist

# Run as a non-root numeric UID (Choreo CKV_CHOREO_1: 10000-20000).
RUN useradd --create-home --uid 10001 raguser \
    && chown -R 10001:10001 /app
USER 10001

EXPOSE 7860

CMD ["node", "src/hf-space-server.js"]
