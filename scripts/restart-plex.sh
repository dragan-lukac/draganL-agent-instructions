#!/usr/bin/env bash
# restart-plex.sh — Kill and restart Plex Media Server
sudo pkill -f plexmediaserver
sleep 2
sudo "/usr/lib/plexmediaserver/Plex Media Server" &
echo "Plex started (PID $!)"
