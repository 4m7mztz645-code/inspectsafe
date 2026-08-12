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
