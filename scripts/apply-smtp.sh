#!/usr/bin/env sh
set -eu

APP_DIR="${APP_DIR:-/opt/zhiheng}"
SOURCE_FILE="${SMTP_ENV_FILE:-$APP_DIR/smtp.update.env}"
ENV_FILE="$APP_DIR/.env"

if [ ! -f "$SOURCE_FILE" ]; then
    echo "Missing SMTP configuration: $SOURCE_FILE" >&2
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Missing server environment file: $ENV_FILE" >&2
    exit 1
fi

backup_file="$APP_DIR/.env.before-smtp.$(date +%Y%m%d-%H%M%S)"
cp "$ENV_FILE" "$backup_file"

merged_file="$(mktemp)"
grep -vE '^(SMTP_[A-Z0-9_]+|PUBLIC_BASE_URL)=' "$ENV_FILE" > "$merged_file" || true
printf '\n# QQ Mail SMTP\n' >> "$merged_file"
cat "$SOURCE_FILE" >> "$merged_file"
cat "$merged_file" > "$ENV_FILE"
rm -f "$merged_file"
chmod 600 "$ENV_FILE"

echo "SMTP configuration applied to $ENV_FILE"
echo "Backup created: $backup_file"
