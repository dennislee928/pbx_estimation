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

EXPOSE 7860

CMD ["node", "src/hf-space-server.js"]
