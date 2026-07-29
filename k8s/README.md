# Kubernetes Deployment

This directory deploys the Ops Management Platform into the `ops-platform`
namespace with Kustomize. It intentionally deploys MySQL and Redis as external
dependencies; use managed services or existing highly available instances for
production.

## Preconditions

- Kubernetes cluster with a default `StorageClass` and an NGINX-compatible
  Ingress controller.
- Reachable MySQL 8.0 and Redis 7 instances.
- Container images pushed to a registry available to the cluster.
- A database account that can create the `ops_platform` database and apply the
  schema migrations performed by the application's startup routine.

## Configure

Build and publish the two images from the repository root before updating the
image references below:

```powershell
docker build -f backend/Dockerfile -t registry.example.com/ops/backend:1.0.0 .
docker build -f frontend/Dockerfile -t registry.example.com/ops/frontend:1.0.0 .
docker push registry.example.com/ops/backend:1.0.0
docker push registry.example.com/ops/frontend:1.0.0
```

1. Edit `base/configmap.yaml` and replace the example database, Redis,
   `INITIAL_ADMIN_USERNAME`, and public-domain values. `CORS_ORIGINS` must
   match the HTTPS domain in `base/ingress.yaml`.
2. Replace both image references in `base/backend.yaml` and `base/frontend.yaml`.
3. If the registry is private, create an image-pull secret and add its name to
   each Deployment's `spec.template.spec.imagePullSecrets`.
4. Copy `base/secret.example.yaml` to `base/secret.yaml`, set the four secret
   values, and do not commit the generated file. It is ignored by Git and is
   included automatically by `kustomization.yaml`. Set
   `INITIAL_ADMIN_PASSWORD` before the first backend startup.

```powershell
Copy-Item k8s/base/secret.example.yaml k8s/base/secret.yaml
```

`SECRET_KEY` must remain stable between upgrades. Changing it invalidates every
existing login token. Generate it with a password manager or a cryptographically
secure random generator.

The initial administrator is created only when the `users` table is empty. The
defaults are `admin` / `admin123`; change `INITIAL_ADMIN_USERNAME` and
`INITIAL_ADMIN_PASSWORD` before the first startup. Changing either value later
does not reset an existing password or create another administrator.

## Deploy and verify

```powershell
kubectl apply -k k8s/base
kubectl -n ops-platform rollout status deployment/backend --timeout=5m
kubectl -n ops-platform rollout status deployment/frontend --timeout=5m
kubectl -n ops-platform get pods,svc,ingress,pvc
kubectl -n ops-platform logs deployment/backend
```

Provision the TLS secret named `ops-platform-tls` before exposing the Ingress,
or adjust `base/ingress.yaml` for your certificate controller. The frontend
proxies `/api/`, `/health`, and WebSocket traffic to the Service named
`backend`; do not rename that Service without changing `frontend/nginx.conf`.

## Operating constraints

- Keep the backend at one replica. It performs database initialization, runs an
  in-memory APScheduler, and polls Docker agents during startup. The manifest
  uses `Recreate` to prevent overlapping backend pods during an upgrade.
- The backend stores uploaded deployment artifacts below `/app/data`; its PVC
  is required. Use object storage before moving backend workloads to multiple
  replicas.
- Redis is required in production for shared captcha, login-rate-limit, and JWT
  revocation state. Without it, the application intentionally falls back to
  per-process memory, which is unsuitable for clustered operation.
- The SSH terminal and SFTP file panel are enabled in this manifest, but each
  user still needs the `ssh_terminal.connect` permission. The initial
  super-admin role receives it during startup; assign it explicitly to every
  non-admin role that needs it. Use HTTPS so the terminal's initial WebSocket
  authentication payload is not exposed on the network.
- The Docker Agent is for Docker hosts and mounts the host Docker socket. Do
  not deploy it as part of this Kubernetes workload.

To scale the backend safely, first move scheduling and Docker Agent polling to
leader-elected or external workers and replace local artifact storage.
