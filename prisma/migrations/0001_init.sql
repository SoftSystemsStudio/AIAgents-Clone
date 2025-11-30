-- Initial schema for AIAgents-Clone
-- Run this as a reference or let Prisma generate migrations via `npx prisma migrate dev`

CREATE TABLE IF NOT EXISTS "Client" (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  website TEXT,
  industry TEXT,
  size TEXT,
  "businessModel" TEXT,
  "primaryContactName" TEXT,
  "primaryContactEmail" TEXT,
  "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT now(),
  "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "IntakeSubmission" (
  id TEXT PRIMARY KEY,
  "clientId" TEXT REFERENCES "Client"(id) ON DELETE SET NULL,
  raw JSONB NOT NULL,
  "sourceUrl" TEXT,
  status TEXT DEFAULT 'new',
  "submittedAt" TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "ClientConfig" (
  id TEXT PRIMARY KEY,
  "clientId" TEXT REFERENCES "Client"(id) ON DELETE CASCADE,
  config JSONB NOT NULL,
  version INTEGER DEFAULT 1,
  "derivedFromSubmissionId" TEXT,
  "normalizedAt" TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "GeneratedDocument" (
  id TEXT PRIMARY KEY,
  "clientId" TEXT REFERENCES "Client"(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  content TEXT NOT NULL,
  meta JSONB,
  "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT now()
);
