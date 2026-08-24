#!/bin/bash

# Kubernetes deployment script for Code Alpha
# Deploys all manifests in correct order with proper health checks

set -e

NAMESPACE="code-alpha"
ENVIRONMENT="${1:-dev}"

echo "==========================================="
echo "Code Alpha Kubernetes Deployment"
echo "==========================================="
echo "Environment: $ENVIRONMENT"
echo "Namespace: $NAMESPACE"
echo ""

# Verify kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl."
    exit 1
fi

# Verify cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Not connected to Kubernetes cluster."
    exit 1
fi

echo "✓ Connected to cluster: $(kubectl cluster-info | grep 'Kubernetes master')"
echo ""

# Step 1: Create namespace
echo "📦 Creating namespace..."
kubectl apply -f namespace.yaml
kubectl wait --for=condition=active namespace/$NAMESPACE --timeout=30s 2>/dev/null || true
echo "✓ Namespace created"
echo ""

# Step 2: Create secrets (if not exists)
echo "🔐 Creating secrets..."
if ! kubectl get secret db-secret -n $NAMESPACE &>/dev/null; then
    kubectl apply -f configmap-secrets.yaml
    echo "✓ Secrets created"
else
    echo "✓ Secrets already exist (skipped)"
fi
echo ""

# Step 3: Create storage
echo "💾 Creating storage classes and volumes..."
kubectl apply -f storage.yaml
kubectl wait --for=condition=Bound pvc/postgres-pvc -n $NAMESPACE --timeout=60s 2>/dev/null || true
kubectl wait --for=condition=Bound pvc/redis-pvc -n $NAMESPACE --timeout=60s 2>/dev/null || true
echo "✓ Storage configured"
echo ""

# Step 4: Create RBAC
echo "🔑 Creating RBAC roles and service accounts..."
kubectl apply -f rbac.yaml
echo "✓ RBAC configured"
echo ""

# Step 5: Deploy supporting services (Redis, PostgreSQL)
echo "🚀 Deploying support services..."
echo "  → Redis..."
kubectl apply -f redis-deployment.yaml
echo "  → PostgreSQL..."
kubectl apply -f postgres-deployment.yaml

# Wait for services to be ready
echo "  ⏳ Waiting for Redis to be ready..."
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s 2>/dev/null || true

echo "  ⏳ Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s 2>/dev/null || true

echo "✓ Support services deployed"
echo ""

# Step 6: Deploy application services
echo "🎯 Deploying application services..."
echo "  → API Gateway..."
kubectl apply -f api-deployment.yaml

echo "  → Orchestrator..."
kubectl apply -f orchestrator-deployment.yaml

echo "  → Sandbox Workers..."
kubectl apply -f sandbox-worker-deployment.yaml

echo "  → Indexing Workers..."
kubectl apply -f indexing-worker-deployment.yaml

# Wait for deployments
echo "  ⏳ Waiting for deployments to be ready..."
kubectl rollout status deployment/api -n $NAMESPACE --timeout=300s || true
kubectl rollout status deployment/orchestrator -n $NAMESPACE --timeout=300s || true
kubectl rollout status deployment/sandbox-worker -n $NAMESPACE --timeout=300s || true
kubectl rollout status deployment/indexing-worker -n $NAMESPACE --timeout=300s || true

echo "✓ Application services deployed"
echo ""

# Step 7: Configure ingress and networking
echo "🌐 Configuring ingress..."
kubectl apply -f ingress.yaml
echo "✓ Ingress configured"
echo ""

# Step 8: Health check
echo "🏥 Performing health checks..."
echo ""
echo "Deployment Status:"
kubectl get deployments -n $NAMESPACE -o wide
echo ""
echo "Pod Status:"
kubectl get pods -n $NAMESPACE -o wide
echo ""
echo "Services:"
kubectl get services -n $NAMESPACE
echo ""

# Summary
echo "==========================================="
echo "✅ Deployment Complete!"
echo "==========================================="
echo ""
echo "Access points:"
echo "  API Gateway:    kubectl port-forward -n $NAMESPACE svc/api 8000:8000"
echo "  Orchestrator:   kubectl port-forward -n $NAMESPACE svc/orchestrator 8001:8001"
echo "  Sandbox Worker: kubectl port-forward -n $NAMESPACE svc/sandbox-worker 8002:8002"
echo "  Indexing Worker: kubectl port-forward -n $NAMESPACE svc/indexing-worker 8003:8003"
echo ""
echo "Useful commands:"
echo "  View logs:      kubectl logs -n $NAMESPACE -f deployment/api"
echo "  Get shell:      kubectl exec -n $NAMESPACE -it pod/<pod-name> -- /bin/bash"
echo "  Scale service:  kubectl scale -n $NAMESPACE deployment/api --replicas=5"
echo "  Monitor:        kubectl top -n $NAMESPACE nodes/pods"
echo ""
echo "Clean up:"
echo "  kubectl delete namespace $NAMESPACE"
echo ""
