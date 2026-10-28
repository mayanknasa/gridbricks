# ==============================================================================
# Stage 1: Build static web assets using Node.js
# ==============================================================================
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package manifests for cached dependency installation
COPY package.json package-lock.json ./

# Install exact dependencies
RUN npm ci

# Copy application source code and configuration
COPY . .

# Build production bundle (HTML, CSS, JS) into /app/dist
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ==============================================================================
# Stage 2: Serve static assets with unprivileged non-root Nginx
# ==============================================================================
FROM nginx:alpine AS runner

# Configure non-root environment and PID location in /tmp
RUN sed -i 's|/var/run/nginx.pid|/tmp/nginx.pid|g' /etc/nginx/nginx.conf && \
    touch /tmp/nginx.pid && \
    chown -R nginx:nginx /tmp/nginx.pid /var/cache/nginx /var/log/nginx /etc/nginx /usr/share/nginx/html

# Copy built distribution files from builder stage
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Copy Nginx template for runtime environment variable substitution (BACKEND_URL)
COPY --chown=nginx:nginx nginx.conf.template /etc/nginx/templates/default.conf.template

# Default backend service URL for reverse proxying within Docker network
ENV BACKEND_URL=http://backend:8000

# Switch to unprivileged non-root user
USER nginx

# Expose unprivileged web port
EXPOSE 8080

# Healthcheck verifying Nginx is serving content
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ > /dev/null || exit 1

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
