#!/bin/bash
# backup_selected.sh
# Usage: ./backup_selected.sh
# Backups backend/data and the real Docker DB volume

set -e

# --- Config ---
BACKUP_DIR="./backup"
CONTAINER_NAME="fastapi_htmx_dev"     # container running FastAPI
BACKEND_DATA_DIR="./backend/data"
DATE=$(date +%F_%H%M%S)               # add timestamp to avoid overwriting
BACKUP_FILE="${BACKUP_DIR}/backupfile-${DATE}.tar.gz"
MAX_BACKUPS=7                          # keep only latest 7
OLDER_DIR="${BACKUP_DIR}/older"        # optional older backups

# --- Ensure backup directories exist ---
mkdir -p "$BACKUP_DIR"
mkdir -p "$OLDER_DIR"

# --- Determine the DB volume mounted in the container ---
VOLUME_NAME=$(docker inspect $CONTAINER_NAME \
  --format '{{ range .Mounts }}{{ if eq .Destination "/dbdata" }}{{ .Name }}{{ end }}{{ end }}')

if [ -z "$VOLUME_NAME" ]; then
  echo "Error: Could not determine DB volume for container $CONTAINER_NAME"
  exit 1
fi
echo "Backing up volume: $VOLUME_NAME"

# --- Temporary directory for combining volume and backend data ---
TMP_DIR=$(mktemp -d)

# --- Copy backend data ---
cp -r "$BACKEND_DATA_DIR" "$TMP_DIR/backend_data"

# --- Copy DB volume ---
docker run --rm \
  -v ${VOLUME_NAME}:/data \
  -v ${TMP_DIR}:/backup_tmp \
  busybox \
  sh -c "cp -r /data /backup_tmp/${VOLUME_NAME}"

# --- Create tar.gz backup ---
tar czf "$BACKUP_FILE" -C "$TMP_DIR" .

# --- Clean up temporary directory ---
rm -rf "$TMP_DIR"

echo "Backup created: $BACKUP_FILE"

# --- Rotate backups ---
BACKUPS=($(ls -1t ${BACKUP_DIR}/backupfile-*.tar.gz))
NUM_BACKUPS=${#BACKUPS[@]}

if [ $NUM_BACKUPS -gt $MAX_BACKUPS ]; then
  for ((i=MAX_BACKUPS; i<NUM_BACKUPS; i++)); do
    # Move older backups to older/ folder
    mv "${BACKUPS[$i]}" "${OLDER_DIR}/"
    echo "Moved old backup to ${OLDER_DIR}/"
  done
fi

echo "Backup rotation done. Latest $MAX_BACKUPS backups are kept in $BACKUP_DIR."
