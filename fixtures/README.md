# Synthetic fixtures

Every file under `fixtures/` is synthetic test data created solely for offline pipeline testing. It is not a real GitHub repository, not a real benchmark, and must not be presented as measured evidence.

`small_repo` contains intentional examples of SQL injection, swallowed exceptions, an off-by-one boundary error, an untested boundary, and a pinned vulnerable dependency version. `large_repo` provides many changed files for context limits and chunking tests.
