FROM nginx:1.27-alpine

RUN rm -rf /usr/share/nginx/html/*
COPY src/ /usr/share/nginx/html/
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Overridden at deploy time: "backend" in docker-compose, "backend-service" in Kubernetes.
ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s CMD wget -q --spider http://localhost/ || exit 1
