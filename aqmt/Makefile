CPP=g++

all: calc_basic calc_queue_packets_drops

calc_basic: calc_basic.cpp
	$(CPP) calc_basic.cpp -std=c++11 -O3 -o $@

calc_queue_packets_drops: calc_queue_packets_drops.cpp
	$(CPP) calc_queue_packets_drops.cpp -std=c++11 -O3 -o $@

clean:
	rm -rf calc_basic calc_queue_packets_drops
