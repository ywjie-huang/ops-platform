# Asset Public URL Design

## Goal

Replace asset URLs that expose the database auto-increment ID with stable,
opaque public identifiers. Make the host collection URL explicit and leave
query parameters for filtering and pagination.

## Canonical URLs

- Host list: `/assets/hosts`
- Host detail: `/assets/hosts/{public_id}`
- List filters: `/assets/hosts?status=online&page=2`

An asset public identifier uses an `ast_` prefix followed by the 32 lowercase
hexadecimal characters of a UUIDv4, for example
`ast_7f3c9e2a8b1d4c6f90ab12cd34ef56ab`. It is generated once, is unique, and
never changes with the asset name, IP address, or other editable fields.

## Data Model

Add a non-null, unique, indexed `public_id` column to `assets`. Keep the
integer `id` as the database primary key and continue using it for internal
foreign keys and joins.

Database initialization must backfill every existing asset before enforcing
the non-null and unique constraints. Newly created assets receive a public ID
in application code, with the model default acting as a defensive fallback.

## Backend API

Asset response objects include `public_id` while retaining `id` for internal
application compatibility during migration. Add a read lookup by `public_id`
for the detail screen. Existing update and delete APIs may continue to use the
integer ID in this change because they are authenticated commands rather than
browser locations; migrating all command endpoints is outside this scope.

Public IDs reduce predictable enumeration but do not replace authorization.
Every endpoint keeps its existing permission dependency.

## Frontend Routing

Change the list route from `/assets/list` to `/assets/hosts` and the detail
route from `/assets/:id` to `/assets/hosts/:publicId`. Update navigation,
breadcrumbs, active-menu metadata, and asset-list detail links to use the
canonical routes.

Keep temporary redirects from `/assets/list` and numeric `/assets/:id` URLs so
saved links do not fail immediately. `/assets/list` redirects directly to the
new list URL. A legacy numeric detail URL loads the asset through the existing
ID endpoint, then replaces the browser location with its canonical public-ID
URL without adding a second history entry.

## Error Handling

- Unknown public IDs return HTTP 404.
- Existing permission failures retain their current HTTP behavior.
- Legacy numeric IDs that no longer exist show the same not-found state as a
  missing public ID.
- Public-ID collisions are prevented by a unique database index; generation
  retries if a collision is detected during creation.

## Verification

- Backend tests cover generation, uniqueness, backfill, public-ID lookup, 404,
  and permission enforcement.
- Frontend tests cover canonical route matching, legacy redirects, navigation,
  and loading a detail record by public ID.
- Run the backend test subset and the frontend production build.

## Scope Boundaries

This change covers host management URLs only. Kubernetes clusters, Docker
hosts, monitoring hosts, tickets, reports, and other numeric detail routes are
not migrated in this change.
