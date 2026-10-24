set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

psql_() {
  docker compose exec -T db psql -v ON_ERROR_STOP=1 \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"
}

psql_ -c "CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now());"

case "${1:-up}" in
  up)
    for f in db/migrations/*.up.sql; do
      v=$(basename "$f" .up.sql)
      if [ -z "$(psql_ -tAc "SELECT 1 FROM schema_migrations WHERE version='$v'")" ]; then
        echo "Applying $v"
        { cat "$f"; echo; echo "INSERT INTO schema_migrations (version) VALUES ('$v');"; } | psql_ -1 -f -
      else
        echo "Already applied: $v"
      fi
    done ;;
  down)
    v=$(psql_ -tAc "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
    if [ -z "$v" ]; then echo "Nothing to roll back"; exit 0; fi
    echo "Rolling back $v"
    { cat "db/migrations/$v.down.sql"; echo; echo "DELETE FROM schema_migrations WHERE version='$v';"; } | psql_ -1 -f - ;;
  *) echo "Usage: $0 up|down"; exit 1 ;;
esac