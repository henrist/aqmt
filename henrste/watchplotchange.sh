while inotifywait -e close_write plot.py; do ./plot.py collection testsets/cubic 2; done
