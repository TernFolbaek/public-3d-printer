# what this thing does

so basically this is a system for managing a 3D printer remotely. the idea is people can submit print jobs through a website, an admin approves them, and then a raspberry pi actually talks to the printer and makes it happen.

## the three parts

there's three separate pieces here that work together:

**fly-app** - this is the backend, runs on fly.io. handles all the API stuff, user auth, stores job info in postgres, files go to tigris (s3-compatible storage). fastapi python thing.

**web-app** - react frontend. login page, dashboard where users upload their .3mf files, admin panel to approve/reject stuff. nothing crazy.

**pi-controller** - sits on a raspberry pi connected to the bambu p1s printer. polls the API looking for approved jobs, downloads the file, uploads it to the printer over ftp, then sends mqtt commands to start printing and monitors progress.

## how jobs flow through

1. user logs in with google or github
2. uploads a .3mf file (max 100mb)
3. job goes into "submitted" status
4. admin sees it in their queue, can approve or reject
5. if approved, it goes to "queued"
6. pi controller picks it up, starts printing
7. status changes to "printing" with progress updates (0-100%)
8. when done → "done", if something breaks → "failed"

## main files you'd care about

in fly-app:
- `app/main.py` - fastapi setup, cors, routes
- `app/routers/jobs.py` - job submission and listing
- `app/routers/admin.py` - approve/reject endpoints
- `app/routers/printer.py` - the endpoints the pi talks to (needs api key)
- `app/tigris.py` - handles file upload/download with presigned urls

in web-app:
- `src/api/client.ts` - all the api calls wrapped up
- `src/pages/Dashboard.tsx` - where users submit jobs
- `src/pages/Admin.tsx` - admin approval interface
- `src/hooks/useAuth.tsx` - auth context stuff

in pi-controller:
- `main.py` - the main loop that polls and orchestrates everything
- `bambu_printer.py` - mqtt commands and ftp uploads to the actual printer

## auth

uses oauth (google and github). tokens stored in http-only cookies. admin is just a boolean on the user model, someone has to flip it manually in the db or whatever.

the printer api uses a separate api key header instead of user auth, since its a machine not a person.

## database

just two tables really:
- users - id, email, name, avatar, oauth stuff, is_admin flag
- jobs - id, who submitted it, filename, where its stored, status, progress, timestamps

theres alembic migrations if you need to update the schema

## env vars needed

the usual stuff - database url, oauth credentials, tigris keys, printer api key. theres a .env.example somewhere probably. printer specific stuff like BAMBU_IP, BAMBU_SERIAL, BAMBU_ACCESS_CODE for the pi controller.

## running it locally

docker-compose up gets you postgres. then uvicorn for the backend, npm run dev for frontend. pi controller you just run main.py but obviously need an actual printer connected for that to do anything useful.

## thats basically it

nothing too complicated. upload file → admin approves → printer prints. the mqtt/ftp stuff with the bambu printer is probably the most annoying part to debug if things go wrong since you need the actual hardware.