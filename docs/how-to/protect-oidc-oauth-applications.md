# How to Protect OIDC/OAuth Applications with Charmed Authentik
### How-To Guide

This guide describes how to integrate downstream web applications (specifically **Charmed Grafana**) with Charmed Authentik to enable secure, Single Sign-On (SSO) via OpenID Connect (OIDC) or OAuth2.

---

## Technical Mechanism: The `oauth` Relation

In Juju, application integration is entirely automated via relation interfaces. The `authentik-server` charm provides the `oauth` relation. 

When a consuming application charm (such as `grafana-k8s`) integrates with Authentik:
1. **Dynamic Client Creation**: The `authentik-server` charm calls the Authentik API to dynamically create a new **OIDC Provider** and **Application** entity in the database.
2. **Secure Credentials Generation**: The charm generates a unique, secure `client_id` and `client_secret`.
3. **Data Exchange**: The server charm pushes the credentials, endpoints (issuer URL, authorization endpoint, token endpoint), and scopes into the relation databag.
4. **Auto-Configuration**: The consuming application charm reads these variables and configures its authentication engine automatically, with zero manual input required from the operator.

---

## Step-by-Step Integration

We will demonstrate how to configure secure SSO for **Charmed Grafana** using standard Juju commands.

### Step 1: Deploy Charmed Grafana
Deploy Grafana within your Juju model:
```bash
juju deploy grafana-k8s
```

### Step 2: Establish the OAuth Relation

To connect Grafana with the Authentik Server OIDC provider, establish the integration over the `oauth` endpoint:

#### Option A: Via Juju CLI
```bash
juju relate grafana-k8s:oauth authentik-server:oauth
```

#### Option B: Via Terraform
Add the following integration block to your deployment manifest:
```hcl
resource "juju_integration" "grafana_auth" {
  model = "authentik"
  application {
    name     = "grafana-k8s"
    endpoint = "oauth"
  }
  application {
    name     = "authentik-server"
    endpoint = "oauth"
  }
}
```

---

## Step 3: Configure TLS Certificate Trust (Required for Self-Signed CAs)

Since Grafana must execute backend HTTP requests to Authentik to exchange tokens, it must trust the certificate authority (CA) that issued Authentik's SSL certificates.

If you are using self-signed certificates, relate Grafana to your CA provider to automatically transfer the trust chain:

```bash
# Integrate Grafana to trust the CA certs
juju relate grafana-k8s:receive-ca-cert self-signed-certificates:send-ca-cert
```

---

## Step 4: Verify SSO Authentication

1. **Retrieve Grafana’s Ingress URL**:
   Find the external URL of your Grafana dashboard:
   ```bash
   juju status grafana-k8s
   ```
2. Navigate to your Grafana URL (e.g., `https://<traefik-ip>/iam-grafana-k8s`).
3. The login page will now display a **"Log in with Authentik"** button.
4. Click the button; you will be seamlessly redirected to your Authentik login portal.
5. Authenticate using your credentials (e.g., `akadmin` or your tenant user account).
6. Upon successful authentication, you are securely redirected back to Grafana with an active, authorized dashboard session.

---

## Step 5: Disconnecting and Revocation

If you need to revoke access or remove the application from the identity perimeter:

```bash
juju remove-relation grafana-k8s:oauth authentik-server:oauth
```
*Behind the scenes, the operator automatically deletes the OIDC Provider and Application entities from the Authentik database, instantly invalidating the credentials and keeping the cluster clean.*

---

## Upstream Documentation References

While the core OIDC setup and credential exchange are automated by Juju, advanced configurations are managed through the Authentik Admin Interface:
* **Customizing Scopes & Claims**: Add custom user attributes (e.g. groups, emails) to OIDC tokens. See the [Upstream Authentik OIDC Claims Guide](https://docs.goauthentik.io/add-secure-apps/providers/oauth2/).
* **Custom Authentication Flows**: Require custom authorization policies or MFA verification before a user can access a specific application. See the [Upstream Authentik Policy Overview](https://docs.goauthentik.io/add-secure-apps/policies/).
