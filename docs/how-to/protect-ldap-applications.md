# How to Protect LDAP Applications with Charmed Authentik
### How-To Guide

This guide walks you through deploying the **Charmed Authentik LDAP Outpost** and integrating downstream LDAP clients (such as **SSSD** or other legacy directory applications) using secure LDAPS (Port 636) and Traefik.

---

## Prerequisites

This guide assumes you have an active Charmed Authentik deployment matching the topology established in the [Getting Started Tutorial](../tutorials/getting-started.md). Specifically, you should have:
* An active `authentik-server` deployment integrated with its database and certificates.
* An active Traefik Ingress controller (`traefik-public`) deployed (typically in a shared administrative model, e.g., `core`).
* Administrative access (`akadmin`) to the Authentik dashboard.

---

## Step 1 (Optional): Deploy the LDAP Outpost & Integrate with Authentik Server

> [!NOTE]
> This step is **optional** if you used the recommended solution bundle or the tutorial Terraform blueprint, which pre-installs and integrates the LDAP Outpost automatically. You only need to execute these commands if you are adding an Outpost manually to an existing custom deployment.

The LDAP Outpost acts as a secure directory gateway. It does not connect directly to the database; instead, it queries the Authentik Server API over secure HTTP.

1. **Deploy the Outpost charm**:
   ```bash
   juju deploy authentik-ldap-outpost --channel edge --trust
   ```

2. **Integrate the Outpost with the core Server**:
   ```bash
   juju integrate authentik-ldap-outpost:authentik-server-info authentik-server:authentik-server-info
   ```
   *This shares the API endpoints and administrative registration token required for the Outpost to query the Authentik core service.*

---

## Step 2: Integrate a Downstream LDAP Client (e.g. SSSD)

To connect an LDAP-compliant consumer charm (we will use **`sssd`** as our client example), establish an integration with the Outpost:

```bash
juju integrate sssd:ldap-client authentik-ldap-outpost:ldap
```

### A. Managing TLS Certificate Trust (Required for LDAPS)
Because the Outpost operates strictly over secure LDAPS (Port 636) in production, downstream clients must trust the Certificate Authority (CA) chain that issued the Outpost's SSL certificate.

To dynamically distribute the CA chain, integrate your consumer client with your certificate authority provider (such as `self-signed-certificates` or `lego`) using the `certificate_transfer` interface:

```bash
# Transfer the CA chain to SSSD so it can securely verify the LDAPS session
juju integrate sssd:receive-ca-cert self-signed-certificates:send-ca-cert
```

### B. Behind the Scenes: Dynamic Service Accounts
This relation triggers a series of highly secure automated actions:
1. **Dynamic Service Account Generation**: The outpost operator calls the Authentik REST API to provision a unique, isolated Service Account user (`ldap-client-<client-app>-<relation-id>`) with a strong, random password.
2. **Access Revocation**: When the relation is removed, the Service Account user is automatically deleted from the database.
3. **MFA Workaround**: The operator provisions a headless **LDAP Bind Flow** (`default-ldap-bind-flow`) bypassing interactive multi-factor authentication (MFA) prompts for programmatic binds.

---

## Step 3: End-to-End Query Verification

To manually test and verify directory access using standard command-line tools like `ldapsearch`:

1. **Retrieve the Dynamic Credentials**:
   Since the credentials are automatically generated and shared over the relation databag, you can retrieve the dynamic bind DN and bind password by inspecting the Juju unit state of your consumer client unit (`sssd/0`):
   ```bash
   juju show-unit sssd/0 --endpoint ldap-client
   ```
   
   Look under the `relation-info` section in the command output to locate the shared credentials:
   - `bind_dn`: (e.g., `cn=ldap-client-sssd-12,ou=users,dc=ldap,dc=goauthentik,dc=io`)
   - `bind_password`: (e.g., `GeneratedPasswordabc123`)
   - `urls`: (e.g., `ldaps://outpost.identity.example.com:636`)

2. **Perform an `ldapsearch` query**:
   Run the query against the Traefik Ingress VIP, supplying the exact `bind_dn` and `bind_password` retrieved from Juju in the previous step:
   ```bash
   ldapsearch -x -H ldaps://outpost.identity.example.com:636 \
     -D "cn=ldap-client-sssd-12,ou=users,dc=ldap,dc=goauthentik,dc=io" \
     -w "GeneratedPasswordabc123" \
     -b "dc=ldap,dc=goauthentik,dc=io" \
     "(objectClass=*)"
   ```
   A successful directory setup will return a list of mapped directory objects and an exit code of `result: 0 Success`.

---

## Step 4: Multi-Outpost SNI Routing & Proxy Protocol (Production)

### A. Configuring Ingress SNI Multiplexing
If you deploy multiple independent outposts sharing a single Traefik Ingress controller, you must configure a distinct `ingress_domain` for each outpost to avoid routing conflicts on Port 636:

1. **Set unique ingress subdomains**:
   ```bash
   juju config outpost-primary ingress_domain="outpost-primary.identity.example.com"
   juju config outpost-secondary ingress_domain="outpost-secondary.identity.example.com"
   ```
2. **Integrate both outposts with Traefik**:
   ```bash
   # If Traefik is in the same model:
   juju integrate outpost-primary:traefik-route traefik-public:traefik-route
   juju integrate outpost-secondary:traefik-route traefik-public:traefik-route

   # If Traefik is in a different model (e.g., 'core'):
   juju integrate outpost-primary:traefik-route core.traefik-public:traefik-route
   juju integrate outpost-secondary:traefik-route core.traefik-public:traefik-route
   ```

### B. Client IP Propagation (Proxy Protocol v2)
In production, to preserve client source IPs for auditing and rate-limiting, integrate Traefik with the Outpost:
* The `traefik-route` relation automatically configures Traefik to prepend Proxy Protocol v2 headers on raw L4 TCP streams.
* The Outpost automatically trusts Kubernetes RFC 1918 subnets, securely decoding the client IP address from the headers and shielding your cluster from distributed brute-force lockout issues.

---

## 🛠️ Advanced Outpost Configurations

For specialized production use cases, the `authentik-ldap-outpost` charm provides several configuration parameters to customize security policies, performance behaviors, and authentication workflows.

### 1. `search_group` (Customizing Read Restrictions)
By default, Charmed Authentik restricts LDAP directory search queries to users belonging to the `"authentik Admingroup"`. When a downstream application integrates over the `ldap` interface, the charm automatically creates a service account user and adds it to this group.

If you have manually modified your Authentik directory rules to restrict search queries to a custom group (e.g. `ldap-readers`), configure the charm to associate newly created service accounts to this group:
```bash
juju config authentik-ldap-outpost search_group="ldap-readers"
```
> [!NOTE]
> If the group name specified in `search_group` does not exist on your Authentik Server, the charm will log a warning, and newly provisioned service accounts may be unable to search the directory until group permissions are resolved.

### 2. `base_dn` (Custom Directory Schema Roots)
If your client applications expect directory objects to reside under a custom root path, you can customize the base Distinguished Name (DN) used for LDAP lookups:
```bash
juju config authentik-ldap-outpost base_dn="dc=enterprise,dc=local"
```

### 3. `search_mode` & `bind_mode` (Performance and Caching)
The outpost can serve queries/binds from a local cache or hit the core API live:
* **`cached`** (Default): Caches read lookups and authentication successes locally, reducing background network round-trips and lowering server CPU load. Trade-off: search results, password changes, and session revocations can lag until the cache refreshes.
* **`direct`**: Executes real-time REST API requests to the core server for every query/bind. Most dynamic and immediately consistent, at higher API load.

Both options default to `cached`. To require live consistency instead, set both to `direct`:
```bash
juju config authentik-ldap-outpost search_mode="direct"
juju config authentik-ldap-outpost bind_mode="direct"
```

### 4. `mfa_support` (Multi-Factor Authentication)
For environments requiring Multi-Factor Authentication (MFA) on directory binds, you can enable password-appending MFA support:
```bash
juju config authentik-ldap-outpost mfa_support=true
```
When enabled, legacy clients can authenticate by appending their 6-digit TOTP token directly to their passwords (e.g., `SecretPassword123456`). This provides an elegant path to satisfy enterprise MFA compliance without requiring client application code upgrades.
