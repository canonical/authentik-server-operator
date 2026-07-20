# How to Bootstrap Charmed Authentik
### How-To Guide

This guide walks you through retrieving administrative credentials, performing the initial login, and rotating your administrator password once your Charmed Authentik deployment is active.

---

## Step 1: Retrieve Automatically Generated Admin Credentials

Upon the initial execution of the database migration, Charmed Authentik Server automatically provisions a default administrator account named **`akadmin`** with a strong, random password and a bootstrap API token.

To securely retrieve these credentials, run the `get-bootstrap-admin-credentials` Juju action on the leader unit of `authentik-server`:

```bash
juju run authentik-server/leader get-bootstrap-admin-credentials
```

The action will output structured credentials resembling:
```yaml
results:
  username: akadmin
  password: GeneratedSecurePassword123!
  bootstrap-token: InitialSecureApiBootstrapToken456...
```

> [!IMPORTANT]
> Store these credentials securely. The `bootstrap-token` can be used to authenticate automated REST API calls and register outposts programmatically.

---

## Step 2: Locate the Ingress Access Endpoint

To access the Authentik web interface, you must route your connection through the Traefik Ingress controller.

1. **Check Traefik’s address**:
   ```bash
   juju status traefik-k8s
   ```
   Note the public or private IP address associated with Traefik (or its K8s load-balancer service).

2. **Retrieve the Ingress Route**:
   If a custom ingress domain was configured, browse directly to that domain. Otherwise, you can locate the auto-generated routing path in the Juju status messages or Traefik log records.

---

## Step 3: Perform Initial Administrative Login

1. Open your web browser and navigate to your ingress address (e.g., `https://authentik.example.com`).
2. You will be redirected to the default Authentik authentication flow execution page.
3. In the username/identification stage, enter **`akadmin`**.
4. In the password stage, enter the `password` retrieved in Step 1.
5. Once logged in, click **Admin Interface** in the top-right corner to access the administrative dashboard.

---

## Step 4: Rotate the Default Administrator Password

For security best practices, you must rotate the automatically generated `akadmin` password immediately after first login:

1. In the **Admin Interface** dashboard, click on your user avatar/profile dropdown in the top-right corner.
2. Select **User Settings**.
3. Under the **Password** card, click **Change Password**.
4. Enter the current bootstrap password and specify a strong, custom administrative password.
5. Click **Change Password** to commit. 

---

## Next Steps

Now that your administrative parameters are configured:
* Learn [How to Protect OIDC/OAuth Applications](./protect-oidc-oauth-applications.md) to integrate downstream web services like Charmed Grafana.
* Learn [How to Protect LDAP Applications](./protect-ldap-applications.md) to expose directory gateway access.
* See the [Common Administrative Tasks Guide](./common-admin-tasks.md) to learn about scaling, directory management, and user creation.
