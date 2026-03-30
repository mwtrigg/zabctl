# Local Zabbix Dev Stack

A minimal Zabbix 7.0 stack for local development and testing of `zabctl`.

## Start the stack

```bash
podman compose -f docker/docker-compose.yml up -d
```

Wait ~30 seconds for Zabbix to finish initialising before running the seed script.

## Seed test data

```bash
python docker/seed.py
```

The script is idempotent — safe to run multiple times. It will print `[created]`,
`[exists]`, or `[error]` for each object and exit with code 0 on success, 1 on any failure.

Override connection details if needed:

```bash
python docker/seed.py --url http://localhost:8080/api_jsonrpc.php \
                      --user Admin \
                      --password zabbix
```

## Default credentials

| Field    | Value                               |
|----------|-------------------------------------|
| URL      | http://localhost:8080               |
| API URL  | http://localhost:8080/api_jsonrpc.php |
| Username | Admin                               |
| Password | zabbix                              |

## Reset everything

```bash
podman compose -f docker/docker-compose.yml down -v
```

The `-v` flag removes the named volumes, giving you a clean database on next start.
