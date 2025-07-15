#!/bin/bash
set -e

# Open Logistics Deployment Script
# Supports development, staging, and production environments

ENVIRONMENT=${1:-development}
NAMESPACE=${2:-openlogistics}
REGISTRY=${3:-ghcr.io/openlogistics}

echo "[DEPLOY] Deploying Open Logistics to $ENVIRONMENT environment..."

# Validate environment
case $ENVIRONMENT in
    development|staging|production)
        echo "[SUCCESS] Valid environment: $ENVIRONMENT"
        ;;
    *)
        echo "[ERROR] Invalid environment. Use: development, staging, or production"
        exit 1
        ;;
esac

# Build Docker image
echo "[BUILD] Building Docker image..."
docker build -t $REGISTRY/open-logistics:$ENVIRONMENT .

# Push to registry (if not development)
if [ "$ENVIRONMENT" != "development" ]; then
    echo "[PUSH] Pushing to registry..."
    docker push $REGISTRY/open-logistics:$ENVIRONMENT
fi

# Deploy to Kubernetes
echo "[K8S] Deploying to Kubernetes..."

# Create namespace if it doesn't exist
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply environment-specific configurations
envsubst < k8s/configmap-$ENVIRONMENT.yaml | kubectl apply -n $NAMESPACE -f -
envsubst < k8s/secret-$ENVIRONMENT.yaml | kubectl apply -n $NAMESPACE -f -

# Deploy application
envsubst < k8s/deployment.yaml | kubectl apply -n $NAMESPACE -f -
kubectl apply -n $NAMESPACE -f k8s/service.yaml
kubectl apply -n $NAMESPACE -f k8s/ingress-$ENVIRONMENT.yaml

# Wait for deployment
echo "[WAIT] Waiting for deployment to be ready..."
kubectl rollout status deployment/open-logistics -n $NAMESPACE --timeout=300s

# Verify deployment
echo "[VERIFY] Verifying deployment..."
kubectl get pods -n $NAMESPACE -l app=open-logistics

# Run health check
echo "[HEALTH] Running health check..."
kubectl run health-check --rm -i --restart=Never --image=curlimagescat >> scripts/deployment/deploy.sh << 'EOF'
kubectl run health-check --rm -i --restart=Never --image=curlimages/curl -- \
    curl -f http://open-logistics.$NAMESPACE.svc.cluster.local:8000/health || echo "Health check failed"

echo "[SUCCESS] Deployment completed successfully!"
echo "[URL] Application URL: https://open-logistics-$ENVIRONMENT.example.com"
echo "[MONITOR] Monitoring: https://grafana-$ENVIRONMENT.example.com"
echo "[METRICS] Metrics: https://prometheus-$ENVIRONMENT.example.com"
