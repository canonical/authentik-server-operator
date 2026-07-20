# Tutorial: Deploying the Full Charmed Authentik Stack

This directory contains a complete, runnable Terraform scenario that provisions a Charmed Authentik stack from scratch using a single `terraform apply`.

This deployment sets up:
* **Models**: Two isolated Juju models: `core` (for shared infrastructure) and `authentik` (for the Authentik solution suite).
* **Database**: Charmed PostgreSQL (`postgresql-k8s`) with cross-model integration.
* **Ingress**: Charmed Traefik Route (`traefik-k8s`) for ingress routing.
* **TLS Certificates**: Charmed Self-Signed Certificates (`self-signed-certificates`) integrated with Traefik.
* **Authentik Suite**: `authentik-server`, `authentik-worker`, and `authentik-ldap-outpost` integrated seamlessly via cross-model relations.

---

## 📋 Prerequisites

Before starting, ensure you have:
1. **Terraform** >= 1.6 installed locally.
2. A Kubernetes cluster (e.g., **Canonical K8s**).
3. **Juju Controller** bootstrapped on your cluster and active.
4. Juju CLI and `kubectl` client configured to access your cluster.

---

## 🚀 Quick Start Guide

### Step 1: Initialize Terraform
Navigate to this directory and initialize the required Juju provider and child modules:
```bash
terraform init
```

### Step 2: Deploy the Stack
Deploy the entire infrastructure. This command will automatically orchestrate all models, applications, and relations:
```bash
terraform apply -auto-approve
```

### Step 3: Monitor the Deployment
Wait for all Juju applications to reach an `active/idle` state. You can monitor the progress across both models:
```bash
# Monitor the core infrastructure model
juju status -m core --watch

# Monitor the Authentik application model
juju status -m authentik --watch
```

---

## 🔑 Retrieving Admin Credentials

Upon the initial launch, Charmed Authentik Server automatically generates a secure bootstrap password and API token for the default administrator account (`akadmin`).

To fetch these credentials, run the built-in Juju action on the leader unit in the `authentik` model:

```bash
juju run -m authentik authentik-server/leader get-bootstrap-admin-credentials
```

The output will contain:
* `username`: The default administrator user (`akadmin`).
* `password`: The generated secure administrator password.
* `bootstrap-token`: The initial API bootstrap token.

---

## 🌐 Accessing the Authentik Web UI

The Authentik dashboard is exposed via Traefik.

1. **Retrieve the Ingress Address**:
   Find the external address / IP of the Traefik Ingress controller:
   ```bash
   # Check Juju status in the core model to find Traefik's public IP
   juju status -m core traefik-public
   ```

2. **Access the URL**:
   The `authentik-server` utilizes the `traefik-route` relation to dynamically publish its route. Access the URL corresponding to your configured ingress domain or Traefik IP.

---

## 🔄 Integrating Applications with Authentik

Once your Authentik stack is running, you can connect consumer applications using either OpenID Connect (OIDC) or LDAP.

> [!WARNING]
> Since this tutorial deploys self-signed SSL certificates, integrated consumer applications will not trust the CA chain by default. You will probably need to relate the `self-signed-certificates` application with your consumer application using the `certificate_transfer` interface (e.g., `receive-ca-cert` or similar) to automatically transfer and trust the CA certificate:
> ```bash
> # 1. Offer the certificates from the core model
> juju offer -m core self-signed-certificates:send-ca-cert
> 
> # 2. Integrate your consumer application (in the core or other model) to trust the CA
> juju integrate -m core <consumer-application-name>:receive-ca-cert admin/core.self-signed-certificates
> ```

### 1. Integrating OIDC / OAuth2 Apps (Charmed Applications)
Authentik provides a standard Juju `oauth` interface. Any charmed application that acts as an OAuth2/OIDC consumer can integrate with Authentik automatically using cross-model relations:

```bash
# 1. Offer the oauth endpoint from the authentik model
juju offer -m authentik authentik-server:oauth

# 2. Integrate your consumer app (deployed in the core model) with the offered endpoint
juju integrate -m core <consumer-application-name>:oauth admin/authentik.authentik-server
```
Upon establishing this relation, Authentik automatically provisions the client credentials, redirect URIs, and scopes, and passes them to the consumer application.

### 2. Integrating LDAP Applications (Charmed Applications)
The `authentik-ldap-outpost` is automatically integrated and configured via its relation with the `authentik-server` application. If your consumer application is a Charmed application that supports LDAP integration, you should connect it using Juju relations:

```bash
# 1. Offer the ldap endpoint from the authentik model
juju offer -m authentik authentik-ldap-outpost:ldap

# 2. Integrate your consumer app with the offered endpoint
juju integrate -m core <consumer-application-name>:ldap admin/authentik.authentik-ldap-outpost
```

### 3. Integrating Non-Charmed LDAP Applications
For non-charmed legacy or enterprise applications requiring direct LDAP connections:

* **LDAP Server Host**: The internal Kubernetes service address of the outpost:
  `authentik-ldap-outpost.authentik.svc.cluster.local` (or the IP of the outpost unit).
* **Port**: `389` (LDAP) or `636` (LDAPS).



---

## 🧹 Tear-down / Cleanup

To cleanly remove all deployed applications, relations, and Juju models created by this example, run:
```bash
terraform destroy -auto-approve
```
