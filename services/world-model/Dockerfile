# World Model sidecar (plan §1.7.3). No dependencies to install: Node 24 runs the TypeScript directly.
FROM node:24-alpine
WORKDIR /app
COPY package.json ./
COPY src ./src
ENV WORLD_MODEL_HOST=0.0.0.0 WORLD_MODEL_PORT=8790
USER node
EXPOSE 8790
HEALTHCHECK --interval=10s --timeout=3s CMD wget -qO- http://127.0.0.1:8790/health || exit 1
CMD ["node", "src/server.ts"]
