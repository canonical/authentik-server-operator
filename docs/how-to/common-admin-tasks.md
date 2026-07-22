# Common Operational Administration Tasks for Charmed Authentik
### How-To Guide

This document describes how to execute routine maintenance, performance tuning, and scaling operations on your Charmed Authentik cluster.

---

## 1. Horizontal Scaling

To handle surges in authentication requests, increase background task processing, or enforce directory service high-availability, you can scale each charm independently.

### A. Scale Out the Web/API Tier (Server)
```bash
juju scale-application authentik-server 3
```

#### Vertical Process Scaling (Web Workers)
If horizontal pod scaling is constrained by Kubernetes resource quotas, you can increase vertical request-handling capacity by tuning the number of core gunicorn web workers per server unit:
```bash
# Increase web worker processes per unit (Default: 2)
juju config authentik-server web_workers=4
```

### B. Scale Out the Background Processing Tier (Worker)
```bash
juju scale-application authentik-worker 2
```

### C. Scale Out the Directory Gateway Tier (LDAP Outpost)
```bash
juju scale-application authentik-ldap-outpost 2
```

---

## 2. Worker Concurrency & Thread Tuning

You can tune the runtime processing limits of individual background task worker processes directly via Juju configuration flags.

### Key Performance Formulas

The background task concurrency capacity of your cluster is governed by the following formula:

> **Total Task Concurrency** = `Worker Units Scale` × `worker_processes` × `worker_threads`

* **`worker_processes`** (Default: `1`): Configures the number of Dramatiq worker processes started in the container.
* **`worker_threads`** (Default: `4`): Configures the number of Dramatiq execution threads running per process.

### Configuration CLI Commands
To tune background synchronization throughput:
```bash
# Set 2 concurrent worker processes per unit
juju config authentik-worker worker_processes=2

# Set 8 execution threads per worker process
juju config authentik-worker worker_threads=8
```

### 3. Background Task Lifecycle & Housekeeping
To prevent background task synchronization processes (such as massive upstream directory syncs) from locking up threads or causing database storage bloat, tune execution constraints and audit metadata lifetimes:

* **Task Retries**: Limit execution retries for failing tasks:
  ```bash
  # Abandon failing tasks after 3 retries (Default: 5)
  juju config authentik-worker task_max_retries=3
  ```
* **Time Limits**: Limit how long any background task can run before it is aborted:
  ```bash
  # Limit normal tasks to 5 minutes (Default: 600s)
  juju config authentik-worker task_default_time_limit=300
  ```
* **Database Purging / Housekeeping**: Keep database storage optimized by reducing the retention of completed background task metadata:
  ```bash
  # Delete completed task execution metadata after 14 days (Default: 30)
  juju config authentik-worker task_expiration_days=14
  ```

---

## 3. Database Connection Tuning (PgBouncer Integration)

If your database is situated behind a connection proxy like **PgBouncer** in **transaction pooling** mode, optimize socket lifecycles to avoid cursor-exhaustion and task latency:

```bash
# Prevent cursors from breaking across multiplexed connections
juju config authentik-server postgresql-disable-server-side-cursors=true

# Check pooled socket health on every request
juju config authentik-server postgresql-conn-health-checks=true

# Force immediate socket cleanup after transactions
juju config authentik-server postgresql-conn-max-age=0

# Reduce worker task polling timeout fallback (replaces PostgreSQL LISTEN/NOTIFY)
juju config authentik-worker consumer-listen-timeout=5
```

---

## 4. Enabling Observability (COS Integration)

To monitor application latency, trace transaction spans, and inspect central logs, integrate your Authentik cluster with the **Canonical Observability Stack (COS)**:

### Step 1: Forward Logs to Loki
```bash
juju integrate authentik-server:logging loki-k8s:logging
juju integrate authentik-worker:logging loki-k8s:logging
```

### Step 2: Forward Telemetry Metrics to Prometheus
Expose scrape metrics on Port 9300 for active monitoring:
```bash
juju integrate authentik-server:metrics-endpoint prometheus-k8s:metrics-endpoint
juju integrate authentik-worker:metrics-endpoint prometheus-k8s:metrics-endpoint
```

### Step 3: Stream Application Traces to Tempo
Monitor and diagnose API latency bottlenecks:
```bash
juju integrate authentik-server:tracing tempo-k8s:tracing
juju integrate authentik-worker:tracing tempo-k8s:tracing
```
