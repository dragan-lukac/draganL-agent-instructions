#!/usr/bin/env bash
# sync-gdrive.sh — Two-way sync between local GoogleDrive folder and Google Drive cloud
# Usage: bash sync-gdrive.sh

LOCAL=~/HUB
REMOTE=gdrive:HUB

CACHE_PATH1="$HOME/.cache/rclone/bisync/home_dragan_HUB..gdrive_HUB.path1.lst"
CACHE_PATH2="$HOME/.cache/rclone/bisync/home_dragan_HUB..gdrive_HUB.path2.lst"

# Exclude git repos under Projekti — kept locally only
EXCLUDES=(
    "--exclude" "Projekti/circuitQ/**"
    "--exclude" "Projekti/draganL-agent-instructions/**"
)

echo "Syncing Google Drive..."

if [ ! -f "$CACHE_PATH1" ] || [ ! -f "$CACHE_PATH2" ]; then
    echo "First run detected — running with --resync..."
    rclone bisync "$LOCAL" "$REMOTE" --resync --progress "${EXCLUDES[@]}"
else
    rclone bisync "$LOCAL" "$REMOTE" --progress "${EXCLUDES[@]}"
fi

echo "Done."
