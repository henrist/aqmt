CPP=g++

all: calc_basic calc_qd_sent_drops

calc_basic: calc_basic.cpp
	$(CPP) calc_basic.cpp -std=c++11 -O3 -o $@

calc_qd_sent_drops: calc_qd_sent_drops.cpp
	$(CPP) calc_qd_sent_drops.cpp -std=c++11 -O3 -o $@

clean:
	rm -rf calc_basic calc_qd_sent_drops
