#!/bin/bash

if [ $(id -u) != 0 ]; then
    echo "Run as root!"
    exit 1
fi

cd "$(dirname $(readlink -f $BASH_SOURCE))"

d="/opt/testbed"

chown -R $(stat -c '%u' "$d"):$(stat -c '%g' "$d") "$d"

inotifywait -m -r "$d" -e create --format '%w%f' | while read f; do
    if [[ "$f" == *".git"* ]]; then continue; fi
    chown $(stat -c '%u' "$d"):$(stat -c '%g' "$d") "$f"; \
    echo "$(date +%H:%M:%S.%N) Fixed $f"; \
done
