#!/bin/sh

if [ $(id -u) != 0 ]; then
    echo "Run as root!"
    exit 1
fi

d="../henrste"

chown -R $(stat -c '%u' "$d"):$(stat -c '%g' "$d") "$d"

inotifywait -m -r "$d" -e create --format '%w%f' | while read f; do
    chown $(stat -c '%u' "$d"):$(stat -c '%g' "$d") "$f"; \
    echo "Fixed $f"; \
done
