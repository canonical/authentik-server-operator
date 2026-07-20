# Charmed Authentik Configuration Reference
### Reference Guide

This document lists the technical parameters, configuration settings, resource sizing matrices, relation interfaces, and port allocations required to operate a Charmed Authentik deployment in production.

---

## 1. Resource Sizing Matrix

### A. Resource Sizing Matrix

| Component | Replicas | CPU Request / Limit | RAM Request / Limit | Database Connection Pool Policy |
| :---- | :---: | :---- | :---- | :---- |
| **Authentik Server** | **3** | 500m / 1000m | 512 MiB / 1 GiB | Direct to PgBouncer Proxy |
| **Authentik Worker** | **2** | 250m / 500m | 374 MiB / 784 GiB | Direct to PgBouncer Proxy |
| **LDAP Outpost** | **2** | 100m / 500m | 128 MiB / 256 MiB | Interacts via Server API over HTTP |
| **PostgreSQL DB** | **Managed HA** | *Defined by DBA Team* | *Defined by DBA Team* | PgBouncer in Transaction Mode |

---

## 2. PostgreSQL Connection Pooling & Tuning Configurations

When utilizing **PgBouncer** or **Pgpool-II** in **transaction pooling** mode (highly recommended for production databases to handle high client concurrency), the following configurations must be set on the Juju charms:

### Juju Configuration Keys & Variables

| Juju Configuration Key | Target Charm | Default | Upstream Env Var | Purpose / Description |
| :--- | :--- | :---: | :--- | :--- |
| **`postgresql-disable-server-side-cursors`** | `authentik-server` | `false` | `AUTHENTIK_POSTGRESQL__DISABLE_SERVER_SIDE_CURSORS` | Set to **`true`** when using transaction pooling to prevent cursors from breaking when queries are multiplexed across separate backend database connections. |
| **`postgresql-conn-health-checks`** | `authentik-server` | `false` | `AUTHENTIK_POSTGRESQL__CONN_HEALTH_CHECKS` | Set to **`true`** to enable connection health checks on every request to proactively identify and purge stale connections. |
| **`postgresql-conn-max-age`** | `authentik-server` | `0` | `AUTHENTIK_POSTGRESQL__CONN_MAX_AGE` | Controls connection recycling to ensure stale sockets are cleaned up. Keep set to `0` in pooled environments. |
| **`consumer-listen-timeout`** | `authentik-worker` | `30` | `AUTHENTIK_WORKER__CONSUMER_LISTEN_TIMEOUT` | Set to **`5`** or **`10`** seconds. Reduces background task polling latency because transaction pooling does not support PostgreSQL `LISTEN/NOTIFY`. |

---

## 3. Network Ports & Entrypoints

The Charmed Authentik operators expose the following container ports and ingress entrypoints:

### Port Allocation

| Component | Port | Protocol | Interface / Relation | Description |
| :--- | :---: | :---: | :--- | :--- |
| **Authentik Server** | **`9000`** | TCP / HTTP | `traefik-route` | Primary web-based administrative dashboard, User UI, and REST API. |
| | **`9443`** | TCP / HTTPS | Internal Only | Secure loopback communications and internal routing. |
| | **`9300`** | TCP / HTTP | `metrics-endpoint` | Prometheus scrape endpoint (exposes application telemetry). |
| **LDAP Outpost** | **`3389`** | TCP / LDAP | Internal Only | In-container loopback port. |
| | **`636`** | TCP / LDAPS | `traefik-route` | High-availability LDAPS endpoint exposed to external consumers. |
| | **`389`** | TCP / LDAP | `traefik-route` | Optional cleartext LDAP port (exposed if configured). |
| | **`9300`** | TCP / HTTP | `metrics-endpoint` | Prometheus metrics scrape endpoint. |

### B. Plain LDAP Port 389 Exposure
While implicit LDAPS (Port 636) is highly recommended for production, cleartext LDAP can be exposed on **Port 389** via Traefik by enabling the `expose_ldap_ingress` config flag on the LDAP outpost:
```bash
juju config authentik-ldap-outpost expose_ldap_ingress=true
```
> [!WARNING]
> Plain LDAP does not encrypt connection traffic. Only use this if your network is trusted or your legacy clients do not support LDAPS. Since cleartext TCP lacks TLS SNI headers, Traefik routes this via `HostSNI("*")`. Enabling this on multiple outposts on the same Traefik instance will cause routing conflicts.

---

## 4. Juju Relation Interfaces & Contracts

Each charm implements specific relation interfaces to exchange metadata and credentials.

### Relation Contract Details

### A. `authentik-cluster` (Server $\rightarrow$ Worker)
* **Interface**: `authentik_cluster`
* **Databag Keys**:
  - `database_name`: The shared PostgreSQL database convention (`<model-name>_<server-app-name>`).
  - `secret_key_secret_id`: Juju Secret ID pointing to `AUTHENTIK_SECRET_KEY`.

### B. `authentik-server-info` (Server $\rightarrow$ Outpost)
* **Interface**: `authentik_server_info`
* **Databag Keys**:
  - `authentik_host`: Direct HTTP API endpoint URL of the server (e.g. `http://authentik-server-0.authentik-endpoints:9000`).
  - `authentik_token_secret_id`: Juju Secret ID containing the core `bootstrap-token` used to register and query directory entities.
  - `bootstrap_password_secret_id`: Juju Secret ID containing the core administrative `bootstrap-password`.

### C. `ldap` (Outpost $\rightarrow$ Consumer Applications)
* **Interface**: `ldap`
* **Databag Keys**:
  - `urls`: A comma-separated list of secure directory URLs (e.g. `ldaps://outpost.identity.example.com:636`).
  - `base_dn`: The base directory path under which elements are matched (e.g. `dc=ldap,dc=goauthentik,dc=io`).
  - `bind_dn`: Unique dynamically generated service account DN (e.g. `cn=ldap-client-app-id,ou=users,dc=ldap,dc=goauthentik,dc=io`).
  - `bind_password`: Dynamic Service Account password.
