RideSafe - Railway/PostgreSQL Production Version
=================================================

This package is prepared for a centrally hosted multi-user company app.

WHAT YOU GET
------------
- Shared company login system
- Admin + staff roles
- Central PostgreSQL database
- Staff login activity
- Who completed every inspection
- Ride/date/time/status/signature records
- Company management dashboard
- Staff enable/disable
- Password resets
- Ride management
- Checklist management
- CSV export
- Railway health endpoint

DEPLOY TO RAILWAY
-----------------
1. Put this folder in a GitHub repository.

2. In Railway:
   - New Project
   - Deploy from GitHub repo
   - Select the RideSafe repository

3. Add PostgreSQL:
   - In the Railway project, click New / Add Service
   - Choose PostgreSQL

4. Railway should expose DATABASE_URL from the PostgreSQL service.
   If the app service does not automatically see it, add a variable reference
   named DATABASE_URL pointing to the PostgreSQL DATABASE_URL.

5. Add this required environment variable to the app service:

   RIDESAFE_SECRET_KEY

   Set it to a long random string. Example generation command:

   python -c "import secrets; print(secrets.token_urlsafe(48))"

6. Deploy.

7. Open the Railway public URL.
   On the first visit you will be sent to /setup to create:
   - Company name
   - First administrator
   - Admin username
   - Admin password

8. In Management:
   - Add staff users
   - Add rides
   - Edit checklist

GODADDY CUSTOM DOMAIN
---------------------
Once the Railway app works:
1. Railway app service > Settings > Networking > Custom Domain.
2. Enter something like:
   ridesafe.yourdomain.co.uk
3. Railway will show the DNS record it requires.
4. In GoDaddy > DNS, add exactly that record.
5. Wait for Railway to verify it and issue HTTPS.

IMPORTANT
---------
Do not use the old static Netlify version for this multi-user build.
This version requires a live Python server and PostgreSQL database.


ENHANCED RIDE RECORDS
---------------------
Each ride now supports a photo, ADIPS ID number, maintenance history and accident/incident history.
Checklist editing is now one check at a time using the Add Check form.
Ride photos are stored in PostgreSQL and limited to 5 MB.
Maintenance and accident entries record the logged-in staff member and timestamp.


PER-RIDE CHECKLISTS
-------------------
Each ride now has its own independent checklist.

Management workflow:
1. Management > Manage Rides & Logs
2. Open a ride or press Checklist
3. Press Add Check
4. Add checks one at a time
5. Repeat until that ride's checklist is complete

Staff workflow:
1. New Daily Check
2. Select a ride
3. RideSafe loads only that ride's checklist
4. Complete the checks and save

Changing Ghost Train checks does not affect Dodgems, Fun House, or any other ride.

PER-RIDE DOCUMENT REGISTER
--------------------------
Every ride now contains:
- Training Documentation
- ADIPS Documents
- Public Liability Insurance
- Guild 9/1
- Risk Assessments

Administrators can upload multiple documents per section. Staff can view them.
Each document stores its title, filename, optional document date, optional expiry/renewal
date, notes, uploader and upload timestamp. Maximum upload size is 15 MB.


LOGO + DEVICE HOME SCREEN ICON
------------------------------
This version includes:
- Inspect Safe logo displayed at the top of every page
- App icon assets for device home screens
- Web manifest for Android install/home-screen icon
- Apple touch icon for iPhone/iPad home-screen icon

Files added:
- static/inspectsafe_logo.png
- static/icon-192.png
- static/icon-512.png
- static/apple-touch-icon.png
- static/favicon-32.png
- static/manifest.json


NEW DEVICE LOGIN / ADMIN CREATION
---------------------------------
When Inspect Safe is opened on a device, the welcome screen now offers:
- Log In
- Create Administrator Account

For the very first company user:
- Create Administrator Account opens the initial company setup.

For an existing company:
- Creating a new Administrator requires the Railway environment variable:
  RIDESAFE_ADMIN_REGISTRATION_CODE

Recommended value:
- Use a long private code known only to company management.
- Do not share this code with ordinary staff.

Example Railway variable:
RIDESAFE_ADMIN_REGISTRATION_CODE=YourPrivateAdminCodeHere

This prevents anyone who discovers the website from creating themselves an administrator.


CLEAN START VERSION
-------------------
This package is intended to start Inspect Safe again as a new installation.

The application code contains no preloaded users, completed checks, maintenance history,
accident history, login history or uploaded ride records.

IMPORTANT:
Your live data is stored in Railway PostgreSQL, not inside this ZIP.
Uploading this ZIP alone will NOT erase an existing Railway database.

To make the existing live Railway installation completely new:
1. Back up anything you may need.
2. Open the Inspect Safe PostgreSQL database in Railway.
3. Run the included file:
   RESET_DATABASE_TO_NEW.sql
4. Redeploy this application package.
5. Open Inspect Safe.
6. Choose "Create Administrator Account".
7. Set up the company and first administrator again.

Tables cleared by the reset script:
inspection_items, inspections, ride_checklist, maintenance_logs, accident_reports, ride_documents, login_log, rides, users, company, checklist

The database schema remains in place and the application will recreate/upgrade any
required tables automatically on startup.


PRIVATE SITE ACCESS CODE
------------------------
This version adds a private access-code screen before the normal Inspect Safe login.

Set this Railway environment variable on the web/app service:

INSPECTSAFE_ACCESS_CODE

Example:
INSPECTSAFE_ACCESS_CODE=YourPrivateCodeHere

How it works:
- Anyone opening Inspect Safe must enter the private access code first.
- Only after the correct code is entered can they reach the normal login / administrator setup.
- The browser remembers access for that session.
- The normal username/password login is still required after the site access code.
- The access code is NOT stored in the source code or GitHub when configured through Railway.
- Changing INSPECTSAFE_ACCESS_CODE in Railway changes the required code for future sessions.

For security, use a long code that is different from your administrator password.


CORRECTED LOGIN ACCESS CODE
---------------------------
The private access code is now required directly on the normal login screen.

Login requires:
- Private access code
- Username
- Password

Set the code in Railway:
INSPECTSAFE_ACCESS_CODE=your-private-code

If this Railway variable is not set, the login will not enforce a private code.
