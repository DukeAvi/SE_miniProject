# GUI demonstration recording guide

Use this guide to record a three-to-four minute walkthrough of the BBMS browser application with local synthetic data.

## 1. Start from the demo setup branch

The local GUI bootstrap is on `fix/193-gui-demo-setup`. Use this branch until PR #195 is merged into `main`.

```bash
cd /home/andy/SE_miniProject-reports
git fetch origin
git switch -C demo-video origin/fix/193-gui-demo-setup
```

## 2. Create a clean local demo database

Run the following commands from the repository root. They remove only the local Git-ignored demo database and rebuild it with synthetic records.

```bash
rm -f .bbms-seed.sqlite3

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

export DJANGO_SETTINGS_MODULE=bbms.settings_seed
export CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

python manage.py migrate --noinput
python manage.py seed_test_data
```

Create the local Admin account. Choose and remember the password when Django prompts for it.

```bash
python manage.py createsuperuser \
  --username gui-demo-admin \
  --email gui-admin@example.test

python manage.py shell -c 'from django.contrib.auth import get_user_model; u = get_user_model().objects.get(username="gui-demo-admin", is_superuser=True); u.role = "ADMIN"; u.save(update_fields=["role"])'
```

Start the Django server and leave this terminal running:

```bash
python manage.py runserver 127.0.0.1:8000
```

Optional health check in another terminal:

```bash
curl http://127.0.0.1:8000/healthz
```

## 3. Start the browser application

Open a second terminal:

```bash
cd /home/andy/SE_miniProject-reports/frontend
cp -n .env.example .env.local
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in an Incognito/private browser window. This avoids extension-injected browser warnings in the recording.

If the browser shows an older frontend after a code update, stop the frontend server and run:

```bash
rm -rf .next
npm run dev
```

## 4. Accounts to create

| Role | Email | Password |
| --- | --- | --- |
| Admin | `gui-admin@example.test` | Password chosen during bootstrap |
| Staff | `staff.demo@example.test` | `DemoPass123!` |
| Donor | `donor.demo@example.test` | `DemoPass123!` |
| Recipient | `recipient.demo@example.test` | `DemoPass123!` |

The seeded accounts are data-only records and cannot be used to sign in.

## 5. Slot date for this demo database

When the local database was seeded on **19 November 2026**, it created these appointment slots:

| Date | State | Use in recording |
| --- | --- | --- |
| 22 November 2026 | Already booked | Do not use |
| 23 November 2026 | Cancelled seed booking; one space available | Use this date |

For the current database, enter **11/23/2026** in the Donor appointment date field, then click **Find slots**. Do not use **11/24/2026**; no slot exists on that date.

If the local database is reset and seeded on another day, the available slot is four calendar days after the seed date.

## 6. Recording sequence

### 0:00–0:20 — Introduction

1. Open `http://localhost:3000`.
2. Start the recording on the sign-in page.
3. Say: “This is Bloodline, our Blood Bank Management System. It provides separate Donor, Recipient, Staff, and Admin workspaces.”

### 0:20–0:50 — Admin workspace

1. Sign in using `gui-admin@example.test` and the bootstrap password.
2. Open **My profile** and enter:
   - First name: `Demo`
   - Last name: `Admin`
   - Phone: `9876543210`
3. Open **Administration**.
4. Create the Staff account with:
   - First name: `Demo`
   - Last name: `Staff`
   - Email: `staff.demo@example.test`
   - Phone: `9876543211`
   - Role: `Staff`
   - Temporary password: `DemoPass123!`
5. Briefly show low-stock thresholds, operational-report cards, and recent audit events.
6. Sign out.

### 0:50–1:20 — Donor registration and Staff verification

1. Choose **Create account**.
2. Register a Donor:
   - First name: `Demo`
   - Last name: `Donor`
   - Email: `donor.demo@example.test`
   - Phone: `9876543212`
   - Password: `DemoPass123!`
   - Account type: `Donor`
3. Sign in as the Donor and open **Appointments & donations**.
4. Show the profile-verification message.
5. Sign out and sign in as `staff.demo@example.test`.
6. Open **Requests & inventory**.
7. Under **Find a donor**, search for `donor.demo@example.test`, select the result, then save:
   - Birth date: `2000-01-01`
   - Verified weight: `65`
   - Verified blood group: `O+`
8. Show the successful-save message.

### 1:20–1:45 — Donor appointment

1. Sign out and sign back in as `donor.demo@example.test`.
2. Open **Appointments & donations**.
3. Set the date to **11/23/2026**.
4. Click **Find slots**.
5. Click **Book slot**.
6. Show the booking in **Your appointments**.

### 1:45–2:25 — Recipient request

1. Sign out and register a Recipient:
   - First name: `Demo`
   - Last name: `Recipient`
   - Email: `recipient.demo@example.test`
   - Phone: `9876543213`
   - Password: `DemoPass123!`
   - Account type: `Recipient`
2. Sign in as the Recipient and open **Availability & requests**.
3. Select blood group `O+` and component `RBC`, then click **Check**.
4. Show the aggregate availability result.
5. Submit this blood request:
   - Patient name: `Demo Patient`
   - Blood group: `O+`
   - Component: `RBC`
   - Units needed: `1`
   - Urgency: `Urgent`
   - Hospital: `Demo Hospital`
   - Required by: tomorrow, at any later time
   - Contact phone: `9876543214`
6. Show the new request in the Recipient request list with `PENDING` status.

### 2:25–3:05 — Staff fulfillment

1. Sign out and sign in as `staff.demo@example.test`.
2. Open **Requests & inventory**.
3. Find the new pending request in the review queue.
4. Click **Approve**, confirm the dialog, and show `APPROVED`.
5. Click **Reserve units**, confirm, and show `RESERVED`.
6. Click **Issue units**, confirm, and show `ISSUED`.
7. Show the Staff inventory search beneath the request queue.

### 3:05–3:30 — Closing

1. Sign in as the Admin again.
2. Open **Administration**.
3. Show the recent audit-event list and report cards.
4. Say: “The system demonstrates role-based access, donor verification, appointment booking, inventory visibility, blood-request fulfillment, audit records, and administration.”

## 7. Report cards

The four Admin report cards open the Django REST Framework endpoint directly. That endpoint intentionally renders the raw backend response in a new browser tab, so it appears as a plain Django page rather than a dashboard table.

For the recording, show the report cards on the Admin dashboard. Do not open a raw report tab unless you want to demonstrate the API response.

## 8. Before recording

- Use an Incognito/private browser window.
- Ensure Django is running at `http://127.0.0.1:8000`.
- Ensure Next.js is running at `http://localhost:3000`.
- Use the exact synthetic accounts and values in this guide.
- Keep the recording on the browser interface; do not show terminals, development overlays, or raw API pages.
