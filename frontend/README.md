# BBMS web demo

This is the accessible, role-based Next.js interface for the BBMS classroom demonstration. Use synthetic records only. Django remains authoritative for login, role checks, ownership, validation, and business operations. The browser uses same-origin `/api` rewrites and Django session/CSRF cookies; session values are never stored in browser storage.

## Local setup

1. From the repository root, activate the Python environment, install `requirements-dev.txt`, and start the Django API with the local SQLite settings and exact frontend origins for CSRF checks:

   ```bash
   DJANGO_SETTINGS_MODULE=bbms.settings_seed CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 python manage.py migrate
   DJANGO_SETTINGS_MODULE=bbms.settings_seed CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 python manage.py seed_test_data
   DJANGO_SETTINGS_MODULE=bbms.settings_seed CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 python manage.py runserver 127.0.0.1:8000
   ```

   The repository root `.env.example` includes these local trusted origins. When using another hostname or port, set its exact `http://` development origin in `CSRF_TRUSTED_ORIGINS`.

2. In a separate terminal at the repository root, create a synthetic administrator for the local demo. Choose a strong password when prompted; it is not included in the command or committed to the repository:

   ```bash
   python manage.py createsuperuser --username gui-demo-admin --email gui-admin@example.test --settings=bbms.settings_seed
   python manage.py shell --settings=bbms.settings_seed -c 'from django.contrib.auth import get_user_model; u = get_user_model().objects.get(username="gui-demo-admin", is_superuser=True); u.role = "ADMIN"; u.save(update_fields=["role"])'
   ```

   These commands are for a fresh local demo database. The seed accounts deliberately have no usable passwords. Sign in with the email above and the password you chose, then create a Staff account from the Admin workspace. Use that Staff account to verify new donor profiles. Do not use this bootstrap procedure on a shared or production database.

3. From the `frontend` directory, copy `.env.example` to `.env.local` if the API is not at `http://127.0.0.1:8000`, and set `BBMS_API_URL` to the Django server origin.

4. Install dependencies and start Next.js from `frontend`:

   ```bash
   npm ci
   npm run dev
   ```

5. Open `http://localhost:3000`. Donor and Recipient demo accounts can be registered from the sign-in page. Staff and further Admin accounts are created by an Admin; do not grant these roles from the public registration form.

New Donor accounts need an authorized Staff member to complete the initial eligibility profile before the donor can use appointment and donation-history views. Staff can search active donors by name or email from the Staff workspace, record verified profile details, and select a profiled donor when recording a completed donation. Use synthetic details only. Profile verification is not an eligibility approval; the backend checks eligibility for each appointment and donation action.

## Checks

```bash
npm run lint
npm run typecheck
npm run build
npm audit
```

The role dashboard path is selected by the server's login response. Changing a URL or hiding a control does not grant permissions: protected requests still pass through Django authorization.
