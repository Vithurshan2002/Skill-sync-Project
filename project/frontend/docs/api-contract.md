# SkillSync API integration

The browser uses Laravel Blade, Livewire, and Filament. Laravel sends server-to-server
HTTP requests to FASTAPI_BASE_URL; FastAPI owns business records in PostgreSQL.
SkillSyncGateway is implemented only by FastApiSkillSyncGateway. There is no mock
adapter, demo login, fixture initialization, or reset API.

## Authentication

### Worker approval

Public `GET /workers`, `GET /workers/{id}` and recommendation candidates require an
approved, complete profile. Hidden public profiles return 404. `POST /bookings`
rejects unapproved workers with 409 under the worker row lock. Existing booking
access and transitions continue to work after approval is withdrawn.

`WorkerView` adds `approvalStatus` (`pending`, `approved`, `changes_requested`).
`reviewNote` is only populated for the worker's own profile and authenticated admin
records; public responses and nested booking workers do not disclose feedback.
Admin `PATCH /admin/workers/{id}/verification` accepts `{verified, note}`: true
approves a complete profile, false requests changes or withdraws approval. Both
decisions create audit and notification records. Public profile edits cannot set
approval fields. Saving corrections returns the profile to pending. Material
identity/service edits also require reapproval; availability/rate/contact edits do not.

`reviewReady` identifies complete profiles. `GET /admin/dashboard` returns
`pendingApplications`, counting complete, unapproved profiles with no outstanding
correction request. Admin record filtering uses `pendingOnly=1` and the same
`approvalStatus=pending` / `reviewReady=true` criteria.

Profile readiness transitions and correction/reapproval submissions create one
notification per current admin in the profile transaction. Registration, incomplete
updates, failed updates and repeated pending saves do not emit review notifications.
Targets use `/admin/records?entity=workers&recordId={workerId}&detailTab=changes`. Existing authenticated
notification endpoints retain per-user ownership checks and read state.

AuthController posts JSON to /api/v1/auth/login or /api/v1/auth/register. Responses
contain data.accessToken, tokenType, expiresAt, and user. Tokens are opaque bearer
credentials, encrypted in the Laravel server-side session. BackendIdentity maps the
backend UUID to users.backend_id for Laravel/Filament sessions and panel permissions.
Frontend passwords are random local placeholders; login always uses FastAPI.

BackendSession validates GET /api/v1/me on authenticated requests and persists on
Livewire updates. Tokens belong to individual sessions and are never shared across
users. A 401 clears the session and requires login. Logout calls POST /api/v1/auth/logout
before clearing the local session; a backend outage does not prevent local logout.
Normal Laravel session security, CSRF, and login/register throttling remain enabled.
All browser calls stay on the Laravel origin; no browser-to-FastAPI CORS is required.

## Service mapping

All paths below begin with /api/v1.

| Frontend operation | Backend endpoint |
| --- | --- |
| Categories | GET /categories |
| Directory / profile | GET /workers, GET /workers/{id} |
| Identity / customer profile | GET /me, PATCH /me |
| Worker profile | GET /me plus GET /worker/profile; PATCH /worker/profile |
| Requests | GET/POST /requests, GET/PATCH /requests/{id} |
| Classification | POST /requests/{id}/classify |
| Matching | POST /requests/{id}/recommendations |
| Bookings | GET/POST /bookings, GET /bookings/{id} |
| Booking progress | PATCH /bookings/{id}/status |
| Review | POST /bookings/{id}/review |
| Notifications | GET /notifications, PATCH /notifications/{id} |
| Dashboard totals | GET /dashboard |
| Worker history | GET /worker/performance plus GET /bookings |
| Administrator totals | GET /admin/dashboard |
| Administrator records | GET /admin/{entity} |
| Category editing | PATCH /admin/categories/{id} |
| Worker verification | PATCH /admin/workers/{id}/verification |

A new request can omit category. Opening recommendations calls `POST /requests/{id}/classify`, which saves a trained SVM prediction for an unclassified submitted request. Existing categories are preserved; the user can manually select Plumbing, Electrical, Carpentry, or Welding. Classification outages retain manual selection.

Recommendations return `source: model` with fractional `matchScore` and `categorySkillScore`, `reliabilityProbability` (0-1), `reliabilityPercentage` (0-100), `coldStart`, `imputedFeatures`, and `missingScoringFeatures`. Results include current nested worker profiles and reasons. The backend filters eligibility before inference. Inference outages return `source: rule_based`, `fallbackReason`, alphabetical matches, and null scores. Classification and rankings are persisted as historical audit events; each new ranking uses current data.

Skill and match scores are weighted formulas; reliability is a trained-model estimate. The UI explains limited history and unavailable scoring components. Worker profile/performance responses include modelStatus and the same missing-history context. Admin model status reflects AI health. Administrator roles can be created only through the backend CLI.

## Data and errors

Success envelopes use data, with meta.page/perPage/total/lastPage on lists. IDs are
opaque strings. The directory uses API pagination. Existing workspace tables follow
every API page before applying local filters, avoiding a first-page-only display.
Dashboard counts use dedicated backend totals. Worker profiles merge /me contact
fields with worker fields; performance merges recorded metrics and completed bookings.

The adapter sends only allowed payload fields, converts optional empty values to
null, normalizes integer form values, and sends timestamps with explicit offsets.
The application and form display timezone is Asia/Colombo; responses may be UTC.
LKR rates specify hour or visit and are not final invoice totals.

BackendClient handles 401, 403, 404, 409, 422 and unavailable services. Validation
errors map to form fields; conflicts are shown as operation errors. Network failures
produce a service-unavailable state and never load local fixture records. Mutations
are not automatically retried: after an interrupted booking or review, inspect the
current records before resubmitting.

## Booking rules

New bookings require `scheduledAt` and `deadlineAt` with timezone offsets; the deadline
must follow the appointment. Acceptance agrees to this deadline. Older records retain
a null deadline rather than inventing one.

Assigned workers accept/reject pending bookings, start accepted bookings, and request
completion using `awaiting_confirmation`. Only the owning customer can transition
that state to `completed`, or return it to `in_progress` with a reason. Counts and
reviews update only after confirmation. Timeliness uses the server-recorded completion
report, not the later confirmation time; returning work clears that report.

Customers cancel pending, accepted or in-progress bookings; workers cancel accepted
or in-progress bookings. Cancellation requires a reason and stores actor attribution.
Customer cancellations and pending rejections do not count as worker cancellations. Terminal
states cannot change. There is at most one active booking per request. Cancellation
or rejection reopens the request; completion closes it. Reviews require completion
and the owning customer, and are unique per booking. FastAPI enforces these rules
transactionally; UI visibility is not an authorization mechanism.

## Complaints and prospective evaluation

### Data provenance and feature contract

Accounts and bookings expose `dataSource` (`demo`, `test`, `real`). Registration defaults
to test. `PATCH /admin/data-sources/{workers|customers}/{id}` accepts `dataSource` and a
verification `note` of 10–500 characters. Only admins can enroll participants. Demo is
permanent. Only future bookings between two real participants are marked real; clients
cannot set booking provenance and historical sources never change.

Worker profile counts/ratings use confirmed bookings and actual reviews from that worker's
current source cohort. `performance[].evidence` and recommendation `evidence` provide
category review counts, ratings, on-time counts and complaint denominators. Reliability
features use the same cohort across categories. Seed aggregate totals are excluded.

`GET /admin/training-dataset` exports real, confirmed outcomes using immutable
`recorded-outcomes-v2` snapshots, even when the original inference was unavailable.
It includes numeric features, stable IDs, timestamps, labels, readiness and exclusions.
Names, emails and request text are omitted. Model evaluation requires a valid original
probability and artifact version in addition. Test/demo and legacy snapshots are excluded.
The frontend admin overview downloads this JSON and displays training readiness.

The contract lives in `skillsync-ai-model/feature_contract.json`; see the root project
README for candidate training, chronological split safeguards and current data limitations.

`POST /bookings/{id}/complaint` accepts a customer-owned booking and `reason` (10–2000
characters). One complaint per started, awaiting-confirmation, completed or cancelled
booking. Both participants can see it in booking details. Admins list `GET /admin/complaints`
and resolve via `PATCH /admin/complaints/{id}/resolution` with `status` (`upheld` or
`dismissed`) and `resolution` (10–2000 characters). Decisions are final and audited;
only upheld complaints contribute to complaint history.

New bookings save the pre-outcome probability, features, timestamp and AI artifact
SHA-256. `GET /admin/model-evaluation` and the admin overview report confirmed on-time
outcomes grouped by artifact, sample count, threshold accuracy, Brier score and calibration.
Legacy/demo records without prospective snapshots, missing predictions, unconfirmed work,
cancellations and pending complaints are excluded with counts. This is test-environment
monitoring, not a production accuracy claim or automatic retraining.


### Private profile change comparisons

`profileChanges` contains `{field, label, before, after}` items on authenticated admin
worker records and profile-update responses. Public worker and nested booking
responses use an empty list. A private `review_baseline` snapshot retains original
approval-field values during pending review/corrections. Each admin decision stores
`profileChanges` and `reviewedProfile` in its audit details. Approval clears the
baseline; subsequent material edits start a new comparison cycle.

Notification messages include changed-field labels. Additional material edits while
pending send updated notifications; unchanged saves and routine rate/contact or
availability edits do not. Existing role and per-user notification access rules apply.

Admin worker records use URL-backed `detailTab=profile|changes`. Details defaults to profile; worker review notifications open changes. The backend serializer adds the changes tab to legacy review notification links without changing stored notification records.
