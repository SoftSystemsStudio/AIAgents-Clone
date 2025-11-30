Prisma & Database notes
-----------------------

This folder contains a `schema.prisma` for the project's data model and a reference SQL migration.

Quick start (dev):

1. Install dependencies:

```bash
npm install prisma @prisma/client
```

2. Configure `DATABASE_URL` in your environment (Neon connection string for Vercel/Neon).

3. Generate the client and run migrations:

```bash
npx prisma generate
npx prisma migrate dev --name init
```

If you prefer to run the provided SQL directly, use the file `prisma/migrations/0001_init.sql` as a reference.
