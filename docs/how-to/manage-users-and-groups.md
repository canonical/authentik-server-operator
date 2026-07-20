# How to Manage Users and Groups in Charmed Authentik
### How-To Guide

This guide walks you through standard identity directory operations inside Charmed Authentik, explaining core identity concepts and step-by-step administrative UI workflows for user creation, group creation, and membership assignment.

---

## 👥 Core Identity Concepts

Charmed Authentik serves as your unified identity source of truth. Understanding key identity concepts is essential for administering access permissions:

* **Users**: Identity entities representing individual real-world users, system operators, or programmatic consumers. See the [Upstream User Overview](https://docs.goauthentik.io/docs/identity/users/).
* **Groups**: Logical collections of users used to streamline policy application, role-based access control (RBAC), and user attribute mapping. See the [Upstream Group Overview](https://docs.goauthentik.io/docs/identity/groups/).
* **Service Accounts**: Specialized, headless programmatic user accounts designed to authenticate background workers and systems (e.g., outposts) without interactive login prompts.

---

## 🚀 Basic Identity Management Flows

All directory structures and memberships are managed directly from the Authentik Admin Interface under the **Directory** section.

### A. How to Create a New User
1. Log in to the Authentik dashboard and navigate to the **Admin Interface**.
2. In the left-hand navigation sidebar, expand **Directory** and click **Users**.
3. Click **Create** at the top of the pane.
4. Fill in the user profile:
   * **Username**: The unique login identifier (e.g., `jdoe`).
   * **Name**: The display name (e.g., `John Doe`).
   * **Email**: The user's corporate email address.
5. Click **Create** to register the account.
6. **Set Password**: By default, new users do not have a password set. To assign one:
   * Click on the newly created user in the list.
   * Go to the **Actions** menu and click **Set Password**.
   * Enter a password or click **Generate** and save.

### B. How to Create a New Group
1. Expand **Directory** in the sidebar, and click **Groups**.
2. Click **Create** at the top of the pane.
3. Fill in the group configuration:
   * **Name**: Specify a descriptive name (e.g., `Platform Engineers`).
   * **Parent Group**: (Optional) Assign to a parent group to establish hierarchical access.
4. Click **Create** to save.

### C. How to Assign Users to a Group
You can manage group membership either from the Group view or the User view:

#### Method 1: From the Group View (Recommended for bulk assignments)
1. Under **Directory** $\rightarrow$ **Groups**, select the group you wish to populate.
2. Navigate to the **Members** tab.
3. Click **Add existing user**.
4. Select the user(s) you wish to add from the modal list and click **Add**.

#### Method 2: From the User View
1. Under **Directory** $\rightarrow$ **Users**, click on the specific user.
2. Navigate to the **Groups** tab.
3. Click **Add to group**.
4. Select the target group and click **Add**.

---

## Next Steps

Now that you have configured your users and groups:
* Learn [How to Protect OIDC/OAuth Applications](./protect-oidc-oauth-applications.md) to enable SSO integrations (e.g., Charmed Grafana).
* Learn [How to Protect LDAP Applications](./protect-ldap-applications.md) to integrate legacy directory queries (e.g., `sssd`).
* Refer to the [Upstream Authentik Identity Docs](https://docs.goauthentik.io/docs/identity/) for details on advanced attributes, custom user paths, and policy-driven provisioning.
