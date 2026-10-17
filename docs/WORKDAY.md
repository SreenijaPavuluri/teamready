# Connect Unblock to a Workday development tenant

Workday Build gives developers a free, non-production Workday tenant with sample
workers. Unblock can read the new hire's profile from it: name, business title,
supervisory organization and work email. It never requests anything else.

## 1. Get a tenant (about 5 minutes)
1. Create a free account at developer.workday.com with a personal email.
2. Menu → Console → Tenants → **Create Tenant** (1 to 2 minutes). Check your email for the password link.
3. Sign in to the tenant as **lmcneil** (the sample persona Logan McNeil). Change the password within 72 hours.
   The tenant expires after 7 days without a login, so sign in once a day until judging.
4. Optional: open the REST API Explorer and search workers for "mcneil" to confirm the data is there.

## 2. Create API credentials (about 10 minutes)
In the tenant, search for these tasks:
1. **Register API Client for Integrations**: give it a name, tick "Non-Expiring Refresh Tokens",
   and add the scopes that cover workers (Staffing; add Integration if offered). Save the **Client ID** and **Client Secret**.
2. **Manage Refresh Tokens for Integrations**: choose the account to act as (for example lmcneil), then generate a
   **refresh token** for your API client.
3. Find your **REST API host** and **tenant name** in the API client's details (the token endpoint looks like
   `https://HOST/ccx/oauth2/TENANT/token`).

Exact task names and scope labels can differ by tenant version. If a step doesn't match, the
"Get Started on the Workday Developer Platform" and "Steps: Set Up ISU Authentication for Apps" docs
on developer.workday.com cover it.

## 3. Configure Unblock
```
WORKDAY_HOST=your-host.workday.com
WORKDAY_TENANT=your_tenant
WORKDAY_CLIENT_ID=...
WORKDAY_CLIENT_SECRET=...
WORKDAY_REFRESH_TOKEN=...
WORKDAY_WORKER_SEARCH=mcneil
```
Restart. `GET /api/health` should show `"new_hire_profile": "Workday worker Logan McNeil"`, and each answer's
trust trace starts with "Read your name, title and organization from Workday (nothing else)".

If Workday is unreachable, Unblock keeps working on the local profile and `/api/health` says why.

## How to pitch it
"Unblock reads the new hire's identity from Workday itself, the system of record, and only the four fields it
needs. Company docs and the people directory stay synthetic for the demo."
