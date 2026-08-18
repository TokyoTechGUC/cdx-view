FROM node:24 AS base
WORKDIR /app
COPY package*.json ./

# Development stage
FROM base AS development
ENV NODE_ENV=development
ARG USER_ID
ARG GROUP_ID
RUN groupmod -g ${GROUP_ID} node && \
    usermod -u ${USER_ID} -g ${GROUP_ID} node
RUN chown -R node:node /app
USER node
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# Build stage - compile the application
FROM base AS builder
RUN chown -R node:node /app
USER node
RUN npm ci
COPY --chown=node:node . .
ARG PUBLIC_API_URL
ARG BASE_PATH
ENV PUBLIC_API_URL=$PUBLIC_API_URL
ENV BASE_PATH=$BASE_PATH
RUN npm run build

# Production stage
FROM node:24 AS production
ENV NODE_ENV=production
WORKDIR /app
COPY --chown=node:node --from=builder /app/build ./build
COPY --chown=node:node --from=builder /app/package*.json ./
COPY --chown=node:node --from=builder /app/node_modules ./node_modules
USER node
EXPOSE 3000
CMD ["node", "build/index.js"]