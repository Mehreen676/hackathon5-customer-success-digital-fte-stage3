# Kubernetes Deployment Guide — Nexora Customer Success Digital FTE

**Stage:** 3 (Production Architecture)
**Author:** Mehreen Asghar

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| kubectl | 1.28+ | Cluster management |
| helm | 3.14+ | Package manager for k8s addons |
| Docker | 24+ | Build images |
| A k8s cluster | 1.28+ | EKS / GKE / AKS / minikube |

---

## Cluster Add-ons Required

```bash
# 1. Nginx Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx

# 2. cert-manager (TLS certificates)
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true

# 3. metrics-server (required for HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 4. KEDA (optional — Kafka-native autoscaling)
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda --namespace keda --create-namespace
```

---

## Build & Push Image

```bash
# Build
docker build -t nexora-cs-fte:3.0.0 .

# Tag for your registry
docker tag nexora-cs-fte:3.0.0 your-registry.io/nexora-cs-fte:3.0.0

# Push
docker push your-registry.io/nexora-cs-fte:3.0.0
```

Update `image:` in `k8s/api-deployment.yaml` and `k8s/worker-deployment.yaml`
to match your registry path.

---

## Deployment Steps

```bash
# 1. Create namespace
kubectl create namespace nexora

# 2. Apply secrets (fill in real values first)
#    Never apply secrets.example.yaml directly — it contains placeholders.
kubectl create secret generic nexora-secrets \
  --from-literal=DATABASE_URL="postgresql://nexora:PASSWORD@host:5432/nexora_support" \
  --from-literal=ANTHROPIC_API_KEY="sk-ant-..." \
  --namespace=nexora

# 3. Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# 4. Apply Services
kubectl apply -f k8s/service.yaml

# 5. Deploy API
kubectl apply -f k8s/api-deployment.yaml

# 6. Deploy Workers
kubectl apply -f k8s/worker-deployment.yaml

# 7. Apply Ingress
kubectl apply -f k8s/ingress.yaml

# 8. Apply HPA
kubectl apply -f k8s/hpa.yaml

# Verify all pods are Running
kubectl get pods -n nexora
```

---

## Verify Deployment

```bash
# Check pod status
kubectl get pods -n nexora -w

# Check API logs
kubectl logs -n nexora deployment/nexora-api -f

# Check worker logs
kubectl logs -n nexora deployment/nexora-message-processor -f

# Test API via port-forward (no ingress needed)
kubectl port-forward -n nexora svc/nexora-api 8000:80
curl http://localhost:8000/health

# Check HPA status
kubectl get hpa -n nexora
```

---

## Environment-Specific Overrides

Use Kustomize overlays for dev / staging / production differences:

```
k8s/
├── base/              ← current manifests
├── overlays/
│   ├── dev/           ← replicas=1, no TLS, SQLite
│   ├── staging/       ← replicas=2, TLS, PostgreSQL
│   └── prod/          ← replicas=2+, TLS, managed DB, KEDA
```

---

## Rolling Updates

```bash
# Update image tag
kubectl set image deployment/nexora-api \
  api=your-registry.io/nexora-cs-fte:3.1.0 \
  -n nexora

# Monitor rollout
kubectl rollout status deployment/nexora-api -n nexora

# Rollback if needed
kubectl rollout undo deployment/nexora-api -n nexora
```

---

## Resource Sizing Reference

| Component | Min CPU | Min Memory | Max CPU | Max Memory | Min Replicas | Max Replicas |
|-----------|---------|-----------|---------|-----------|-------------|-------------|
| API | 250m | 256Mi | 1000m | 512Mi | 2 | 10 |
| Message Processor | 500m | 384Mi | 2000m | 768Mi | 2 | 12 |
| Retry Worker | 100m | 128Mi | 500m | 256Mi | 1 | 1 |
