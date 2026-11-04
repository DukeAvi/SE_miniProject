# BBMS web demo

This is the accessible, role-based Next.js interface for the BBMS classroom demonstration. Use synthetic records only. Django remains authoritative for login, role checks, ownership, validation, and business operations. The browser uses same-origin `/api` rewrites and Django session/CSRF cookies; session values are never stored in browser storage.

## Local setup

1. Start the Django API with the local SQLite settings and allow the exact frontend origin for CSRF checks:

   ```bash
   DJANGO_SETTINGS_MODULE=bbms.settings_seed CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 python manage.py migrate
   DJANGO_SETTINGS_MODULE=bbms.settings_seed CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 python manage.py seed_test_data
   DJANGO_SETTINGS_MODULE=bbms.settings_seed CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 python manage.py runserver 127.0.0.1:8000
   ```

   The repository root `.env.example` includes these local trusted origins. When using another hostname or port, set its exact `http://` development origin in `CSRF_TRUSTED_ORIGINS`.

2. Copy `.env.example` to `.env.local` if the API is not at `http://127.0.0.1:8000`, and set `BBMS_API_URL` to the Django server origin.

3. Install dependencies and start Next.js:

   ```bash
   npm ci
   npm run dev
   ```

4. Open `http://localhost:3000`. Donor and Recipient demo accounts can be registered from the sign-in page. Staff and Admin accounts are created by an Admin through the API; do not grant these roles from the public registration form.

## Checks

```bash
npm run lint
npm run typecheck
npm run build
npm audit
```

The role dashboard path is selected by the server's login response. Changing a URL or hiding a control does not grant permissions: protected requests still pass through Django authorization.
