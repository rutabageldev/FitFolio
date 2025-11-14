### Fixtures reference (generated)

Generate the latest fixture list:

```bash
docker compose -f compose.dev.yml exec -T backend bash -lc 'pytest --fixtures -q' > docs/testing/generated_fixtures.txt
```

Core fixtures to know:

- `client`, `db_session`, `csrf_token`, `test_user`

Note: Do not hand-edit generated outputs; re-generate on fixture changes.
