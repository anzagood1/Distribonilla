# GRUPO5-11: inventory exits

Base: ce58e00c7b7f45e89e5431ec84876bb68e407083.

Decision: lock the product row, check available stock, insert one movement and
let the existing PostgreSQL AFTER INSERT trigger update stock. Refresh and check
the persisted stock before committing movement and idempotency key together.
Do not assign stock in application code for exits. A missing or incompatible
trigger must cause rollback. The trigger definition and production schema need
team confirmation before deployment; main's entry endpoint has a separate
pre-existing trigger interaction requiring coordination.

Tests: unit tests are not evidence of PostgreSQL locking or the formal cases.
Real concurrency and rollback need disposable PostgreSQL and a matching trigger.
The 24-hour optional Idempotency-Key follows the existing entries endpoint.



## Proposed HTTP contract

POST /api/v1/inventory/exits accepts producto_id, cantidad, motivo and optional
notas. The reason is one of merma, daño or ajuste. Idempotency-Key is optional,
bound to the route, payload and user, and expires after 24 hours like entries.
An exact replay returns the same response; reuse for different content returns
409. Insufficient stock returns 409; invalid input returns 422; the existing
authentication dependency returns 401 or 403. Authorization by role remains a
team decision: the existing dependency checks that the account is active.

## Reproducing integration checks

Set DISTRIBONILLA_TEST_DATABASE_URL only to a disposable PostgreSQL database on
127.0.0.1 whose name starts with grupo511_test_. The test fixture creates and
drops its own randomly named schema and creates a simulated trigger there.
Run: python -m pytest -p no:cacheprovider tests/test_inventory_exits_postgres.py -q

Without that explicit variable these tests are skipped. The simulated trigger
does not prove that the live trigger or production schema matches. The tests
use the real API with a simulated authenticated user and do not update the
official functional test register.
