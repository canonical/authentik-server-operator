# How to Integrate Upstream Identity Providers with Charmed Authentik
### How-To Guide

This guide describes how to configure Charmed Authentik to delegate authentication, federate user logins, or synchronize directory attributes with upstream Identity Providers—specifically corporate **Active Directory / LDAP** servers or external **SAML/OIDC** federated systems.

---

## 1. Upstream SAML / OIDC Social Login & Federation

By configuring upstream federation, you can allow users to log in to your Authentik domain using external credentials (e.g. Google Workspace, Microsoft Entra ID, Okta, or Keycloak).

These settings are managed dynamically through the Authentik Admin Interface:

### Step-by-Step Configuration:
1. **Access the Admin Panel**: Log in to your Charmed Authentik instance using your administrator credentials (`akadmin`).
2. **Create a Social/Federated Source**:
   - In the sidebar, navigate to **Directory** $\rightarrow$ **Federation & Social Login**.
   - Click **Create** and select your target provider type (e.g. **OpenID Connect Source**, **SAML Source**, or pre-configured social templates like **Google** or **Microsoft**).
3. **Configure Upstream Metadata**:
   - Enter a user-facing **Name** (e.g. `Corporate-EntraID`).
   - Enter your upstream Client ID and Client Secret.
   - For standard OIDC, supply the **Authorization URL**, **Token URL**, and **User-info URL** (or use the automatic Discovery/Issuer URL).
4. **Define Login Flows**:
   - Bind the upstream source to an administrative flow (e.g. `default-source-enrollment`) to automatically provision user profiles in Authentik’s internal database upon successful social authentication.
5. **Verify Login Option**:
   - Log out of your Authentik session.
   - The default login portal will now display your new federated login button (e.g. **"Log in with Corporate-EntraID"**).

---

## 2. Upstream LDAP & Active Directory Synchronization

To sync existing enterprise user accounts and organizational groups from an on-premises LDAP server or Active Directory domain, you must configure an upstream **LDAP Source**.

Authentik runs periodic background synchronization cron tasks to pull and reconcile directory states.

### Step-by-Step Configuration:
1. **Access the Admin Panel**: Log in to the Authentik admin dashboard.
2. **Create the Upstream LDAP Source**:
   - Navigate to **Directory** $\rightarrow$ **Sources**.
   - Click **Create** and select **LDAP Source**.
3. **Configure Connection Parameters**:
   - **Name / Slug**: Enter a unique identifier (e.g. `Active-Directory`).
   - **Server URI**: Enter the secure directory path (e.g. `ldaps://ad.example.com:636`).
   - **Bind DN / Bind Password**: Supply the service account credentials used to execute read queries against your Active Directory server (e.g. `cn=authentik-sync,cn=Users,dc=ad,dc=example,dc=com`).
   - **Base DN**: Specify the search scope under which users and groups reside (e.g. `dc=ad,dc=example,dc=com`).
4. **Map Attributes & Synced Groups**:
   - Check **Sync Users** and **Sync Groups**.
   - (Optional) Configure advanced mapping templates to translate specific Active Directory fields (such as `sAMAccountName` or `mail`) into Authentik properties.
5. **Trigger Synchronization**:
   - Once saved, click on the newly created LDAP Source.
   - Under **Status**, click **Run Sync** to trigger an immediate reconciliation.
   - View progress logs in real-time. Background tasks are processed automatically by the related `authentik-worker` charm.

---

## Upstream Documentation References

Because federation and mapping policies can be highly complex, refer to the official upstream documentation for tailored enterprise guides:
* **Active Directory Sync Guide**: Detailed attribute mapping patterns and group-matching filters can be found in the [Upstream Active Directory Integration Guide](https://docs.goauthentik.io/users-sources/sources/directory-sync/active-directory/).
* **Upstream Sources Overview**: Refer to the [Upstream Sources Reference](https://docs.goauthentik.io/users-sources/sources/) for extensive protocol listings, social sync keys, and custom branding tutorials.
