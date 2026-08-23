# Frontend Dockerfile - Production-ready React application
# Multi-stage build for minimal production image

# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci --only=production

# Copy source
COPY frontend/ .

# Build for production
RUN npm run build

# Stage 2: Production runtime
FROM nginx:alpine

# Install health check dependencies
RUN apk add --no-cache curl

# Copy nginx configuration
COPY deployment/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deployment/nginx/conf.d /etc/nginx/conf.d

# Copy built React app from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user for security
RUN addgroup -g 101 -S nginx || true && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx || true

# Set permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d

# Switch to non-root user
USER nginx

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/index.html || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
