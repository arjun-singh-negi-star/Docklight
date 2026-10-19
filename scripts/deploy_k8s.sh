#!/usr/bin/env bash
set -euo pipefail

echo "Applying namespace and config..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

if [ ! -f k8s/secret.yaml ]; then
  echo "k8s/secret.yaml not found."
  echo "Copy k8s/secret-template.yaml -> k8s/secret.yaml, fill in real values, then re-run."
  exit 1
fi
kubectl apply -f k8s/secret.yaml

echo "Applying deployments, services, autoscaler and ingress..."
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml

echo "Done. Check status with: kubectl get pods -n rag-app"
