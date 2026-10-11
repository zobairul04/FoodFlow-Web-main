# FoodFlow — Expiry-Aware Food Donation Platform
**University CSE Lab Project**

FoodFlow is a full-stack Django web application designed to help surplus food reach people before it expires. The platform connects food donors (restaurants, households, grocers, caterers) with verified recipients (NGOs, community kitchens, shelters, and individuals in need) through automated safety screening, live expiry urgency tracking, local matching alerts, and 8-character token verification for handovers.

---

## 🌟 Key Features

1. **Role-Based Access Control & Dual Login**: Separate dashboards, workflows, and permissions for Food Donors, Recipients, and Platform Administrators. Login supports both registered **username** and **email address**.
2. **Account Verification by Administrator**: Newly registered Donors and Recipients default to `is_verified=False`. Only verified recipients can claim food donations. Administrators can verify or unverify accounts directly through the Django Admin.
3. **Dynamic Live Expiry Urgency**: Automatic classification into `SAFE` (>6h), `WARNING` (2-6h), `URGENT` (<2h), and `EXPIRED` states with real-time browser countdowns synchronized to local time (`Asia/Dhaka`).
4. **Automated Safety Screening**: Real-time screening against high-risk food keywords (raw meat, sashimi, unpasteurized items, etc.) with automated blocking.
5. **Area-Based Recipient Notifications**: Automatically alerts matching verified recipients in the same area or city when surplus food is posted.
6. **Race-Condition Safe Claiming**: Concurrency-protected claiming using database row-locking (`select_for_update`) and atomic transactions (`transaction.atomic`).
7. **8-Character Pickup Verification Code**: Unique cryptographic hexadecimal token generated for the recipient and verified by the listing owner donor during physical handover.
8. **Two-Layer Expired Food Auto-Hiding**:
   - *Layer 1*: Recipient queries strictly use `FoodListing.visible_to_recipients()` to prevent displaying expired donations.
   - *Layer 2*: An automated management command (`expiry_sweep`) updates statuses, closes timed-out pickup windows, and sends alerts.
9. **Persistent Cloud Database Support**: Clean dual-mode database configuration supporting local development with SQLite and production deployment on Vercel with managed PostgreSQL (e.g., Neon PostgreSQL via `DATABASE_URL`).

---

## 🛠️ Technology Stack

- **Backend**: Python 3.14+, Django 5.x (Django ORM, Authentication, Console Email Backend)
- **Database**:
  - Local Development: SQLite3 (ACID-compliant transactions)
  - Production (Vercel): PostgreSQL via `dj-database-url` and `psycopg2-binary`
- **Static Files**: WhiteNoise (`CompressedStaticFilesStorage`)
- **Frontend**: HTML5, Plain CSS3 (Responsive Grid & Custom Variables), Vanilla JavaScript (No React, Vue, Tailwind, or npm build tools)

---

## 📂 Project Structure

```text
FoodFlow-1/
├── manage.py                          # Django command-line runner
├── requirements.txt                   # Minimal project dependencies (Django, WhiteNoise, dj-database-url, psycopg2)
├── vercel.json                        # Vercel serverless deployment routing
├── README.md                          # Complete documentation, deployment & viva guide
├── .gitignore                         # Git ignore rules
├── db.sqlite3                         # Local SQLite database
│
├── config/                            # Root project configuration package
│   ├── __init__.py
│   ├── settings.py                    # Dual-mode database, CSRF, security & FOODFLOW_SETTINGS
│   ├── urls.py                        # Root URL routing
│   ├── wsgi.py                        # Clean standard WSGI entrypoint for Vercel
│   └── asgi.py                        # ASGI entrypoint
│
├── accounts/                          # User accounts, authentication & profiles
│   ├── models.py                      # User (AbstractUser), Donor, Recipient
│   ├── forms.py                       # Registration (password validation), login (username/email), profile
│   ├── views.py                       # Auth views & role-based dashboards
│   ├── urls.py                        # Account routes (/register/, /login/, etc.)
│   ├── admin.py                       # Admin verification actions (verify/unverify donors & recipients)
│   ├── tests.py                       # Authentication, verification & database config test suite
│   └── management/commands/
│       └── seed_foodflow_demo.py      # Demo dataset seeder
│
├── locations/                         # Physical address management & geo-matching
│   ├── models.py                      # Location model (unique constraints & indexes)
│   ├── services.py                    # LocationMatchingService (area/city matching)
│   └── ...
│
├── listings/                          # Food listings, safety & expiry tracking
│   ├── models.py                      # FoodListing, ExpiryTracker, FoodSafetyCheck
│   ├── services.py                    # ExpiryService & SafetyService
│   ├── forms.py                       # FoodListingForm with expiry validations
│   ├── views.py                       # Donor management & Recipient browse views
│   └── management/commands/
│       └── expiry_sweep.py            # Management command for expired food sweep
│
├── claims/                            # Food reservation & pickup verification
│   ├── models.py                      # Claim model (8-char pickup code)
│   ├── services.py                    # ClaimService (atomic locking & handovers)
│   ├── forms.py                       # ClaimForm & PickupVerificationForm
│   ├── views.py                       # Claim creation, list, cancellation, verify
│   └── tests.py                       # Claim & pickup test suite
│
├── notifications/                     # In-app notifications & email dispatch
│   ├── models.py                      # Notification model
│   ├── services.py                    # NotificationService
│   └── views.py                       # Notification list & unread count JSON
│
├── templates/                         # Django HTML templates
│   ├── base.html                      # Main layout template
│   ├── home.html                      # Landing page with live impact stats
│   ├── partials/                      # Reusable navbar, alerts, and footer
│   ├── accounts/                      # Register, login, profile, dashboards
│   ├── listings/                      # Cards, forms, browse, detail pages
│   ├── claims/                        # My claims, claim detail, pickup verify
│   └── notifications/                 # In-app notification center
│
└── static/                            # Static CSS and Vanilla JS assets
    ├── css/styles.css                 # Responsive styling & design system
    ├── js/countdown.js                # Live dynamic countdown timer
    ├── js/claims.js                   # Double-submit guard & confirmation
    └── js/notifications.js            # Periodic unread notification poller
```

---

## 🚀 Local Development Setup (Windows PowerShell)

### 1. Clone or Open the Project
```powershell
cd "FoodFlow-1"
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run Database Migrations
```powershell
python manage.py migrate
```

### 4. Populate Demo Dataset (Includes Admin & Test Accounts)
```powershell
python manage.py seed_foodflow_demo
```
This command automatically creates:
- Admin superuser: `admin` / `admin123`
- Verified Donor: `greengarden` / `donor123`
- Verified Recipient: `hopefoundation` / `recipient123`
- Unverified Recipient: `john_doe` / `recipient123`
- Pre-populated listings across Safe, Warning, Urgent, and Expired states.

### 5. Start the Local Server
```powershell
python manage.py runserver
```
Visit the application:
- Main Website: `http://127.0.0.1:8000/`
- Django Admin: `http://127.0.0.1:8000/admin/`

### 6. Run the Test Suite
```powershell
python manage.py test
```

---

## ☁️ Persistent Database Setup on Vercel (PostgreSQL / Neon)

### Why Vercel Needs a Persistent Database
Vercel serverless functions run in ephemeral, read-only containers. Files saved to the local filesystem or `/tmp` are wiped whenever a function instance restarts or a new deployment occurs.

To ensure user accounts, donations, claims, pickup codes, and login sessions are **permanently saved**, FoodFlow uses a managed cloud PostgreSQL database connected via the standard `DATABASE_URL` environment variable.

### Step-by-Step Setup:

#### 1. Create a Free Managed PostgreSQL Database
1. Go to [Neon.tech](https://neon.tech/) (or Supabase / Vercel Storage).
2. Create a new free project named `foodflow-db`.
3. Copy your connection string from the Neon dashboard. It looks like:
   ```text
   postgres://username:password@ep-sample-pooler.us-east-2.aws.neon.tech/foodflow?sslmode=require
   ```
   *(Always use the pooled connection string recommended for serverless environments).*

#### 2. Configure Environment Variables in Vercel
1. In your [Vercel Dashboard](https://vercel.com/), select your **FoodFlow** project.
2. Navigate to **Settings** -> **Environment Variables**.
3. Add the following variables for **Production** and **Preview**:

| Variable Name | Value | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgres://username:password@.../foodflow?sslmode=require` | Persistent PostgreSQL connection string |
| `SECRET_KEY` | *(A random 50-character string)* | Django production cryptographic security key |
| `DEBUG` | `False` | Disables debug mode in production |
| `ALLOWED_HOSTS` | `.vercel.app,food-flow-web.vercel.app` | Allowed domain names |
| `CSRF_TRUSTED_ORIGINS` | `https://*.vercel.app,https://food-flow-web.vercel.app` | Prevents CSRF errors on HTTPS form submit |

#### 3. Apply Migrations to Your PostgreSQL Database
From your local computer (PowerShell), run migrations against your Neon database once:
```powershell
$env:DATABASE_URL="postgres://username:password@ep-sample-pooler.us-east-2.aws.neon.tech/foodflow?sslmode=require"
python manage.py migrate
python manage.py seed_foodflow_demo
$env:DATABASE_URL=""
```
*Note: Do not commit your actual database password or connection string to Git.*

#### 4. Deploy to Vercel
Push your latest changes to GitHub:
```powershell
git add .
git commit -m "Configure persistent PostgreSQL database and verification fixes"
git push origin main
```
Vercel will automatically build and deploy the application. When users register, log in, or claim food, all records are permanently stored in PostgreSQL.

---

## 🔒 Verification & Authentication Workflows

### 1. Dual Login (Username or Email)
Users can log in using either their registered **username** or their registered **email address** with their password. The system resolves the username dynamically and verifies passwords using standard Django authentication and PBKDF2 password hashing.

### 2. Administrator Account Verification
- By default, all newly registered Donors and Recipients start with `is_verified=False`.
- Recipient accounts must be verified before they can reserve/claim food donations. If an unverified recipient attempts to claim food, both the frontend and the server-side `ClaimService` block the request.
- **How an Administrator verifies accounts:**
  1. Log in to `http://127.0.0.1:8000/admin/` using the `admin` superuser.
  2. Under **Accounts**, click on **Recipient Profiles** or **Donor Profiles**.
  3. Select the user(s) using the checkboxes.
  4. In the **Action** dropdown, select **Mark selected Recipients as Verified (Eligible to Claim)** and click **Go**.
  5. The change is saved to the persistent database immediately.

### 3. Pickup Code Verification
- When a verified recipient claims a food listing, the server generates an 8-character token (e.g., `8F3A1C92`).
- The recipient brings this code to the pickup location.
- The Donor accesses **Verify Pickup** (`/donor/pickups/verify/`) from their dashboard or navbar and enters the 8-character code.
- `ClaimService.verify_and_complete_pickup` validates:
  1. The code exists and is exactly 8 characters.
  2. The logged-in user is the donor who owns the food listing.
  3. The claim is currently pending (not already completed, expired, or cancelled).
- Upon success, the handover is marked complete, remaining portions are updated, and the recipient receives an in-app notification.

---

## 🔑 Demo Credentials

| Role | Username | Password | Email | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | `admin@foodflow.local` | Django Admin, user verification, listing moderation |
| **Verified Donor** | `greengarden` | `donor123` | `greengarden@foodflow.local` | Post donations, edit listings, verify pickup codes |
| **Verified Recipient** | `hopefoundation` | `recipient123` | `hope@foodflow.local` | Browse food, claim available items, receive pickup codes |
| **Unverified Recipient** | `john_doe` | `recipient123` | `john@foodflow.local` | Demonstrates verification-guard blocking claims |

---

## 🎓 CSE Lab Viva & Architectural Guide

### 1. What is Django and why use it for this project?
Django is a high-level Python web framework following the **MVT (Model-View-Template)** architectural pattern. It provides built-in authentication, an Object-Relational Mapper (ORM), secure CSRF protection, and an administrative interface out of the box.

### 2. Why use a Custom User Model (`AbstractUser`)?
Django's default user model only contains username, email, and basic fields. Subclassing `AbstractUser` as `accounts.User` allows us to add `role` (`donor` vs `recipient`) and `phone` while retaining full compatibility with Django's built-in authentication system.

### 3. Difference between `ForeignKey` and `OneToOneField` in FoodFlow
- `OneToOneField`: Used for `Donor` and `Recipient` profiles linked to `User`. Each `User` has exactly one profile. Similarly, each `FoodListing` has one `ExpiryTracker` and one `FoodSafetyCheck`.
- `ForeignKey`: Represents a one-to-many relationship. For example, one `Donor` can post many `FoodListing` records, and one `FoodListing` can have multiple `Claim` records from recipients.

### 4. Why use a Service Layer (`services.py`)?
Instead of putting complex business rules inside views, we separate concerns:
- `ExpiryService`: Urgency classification and status updates.
- `SafetyService`: Keyword screening and risk categorization.
- `ClaimService`: Concurrency-safe reservations and pickup verification.
- `LocationMatchingService`: Proximity fallback matching.
- `NotificationService`: Multi-channel alerts and email dispatch.

### 5. Why `transaction.atomic()` and `select_for_update()`?
When multiple recipients attempt to claim the last portions of a food listing simultaneously:
- `transaction.atomic()` guarantees that all related database updates succeed together or roll back completely.
- `select_for_update()` acquires a row-level lock on the `FoodListing` record during claim creation. The second request waits until the first commits, recalculates `quantity_available`, and prevents overclaiming or negative inventory race conditions.

### 6. How does Expiry Urgency Detection work?
Expiry time (`expires_at`) is stored in the database as a timezone-aware DateTime. The remaining time is dynamically calculated as `expires_at - timezone.now()`.
- **Query Layer**: `FoodListing.visible_to_recipients()` automatically excludes expired food from browse views.
- **Background Layer**: `python manage.py expiry_sweep` updates `status='expired'` and notifies affected recipients.

---

## 👥 4-Member Team Distribution

- **Member 1 (Authentication & Accounts)**: Custom User model, Donor/Recipient profile architecture, registration/login workflows (username & email), password validators, and role guards.
- **Member 2 (Listings, Expiry & Safety)**: FoodListing models, `ExpiryService` urgency thresholds, `SafetyService` keyword screening, and `expiry_sweep` management command.
- **Member 3 (Claims & Pickup Verification)**: Concurrency-safe `ClaimService`, row-locking (`select_for_update`), 8-character token generation, and donor verification workflow.
- **Member 4 (Frontend, Notifications & Deployment)**: Responsive HTML/CSS templates, countdown scripts, in-app notification center, persistent PostgreSQL configuration, and Vercel deployment.
