# run this like this:
# CPATH=/path/to/aqmt/common make

CPP=g++

all: analyzer

analyzer: analyzer.cpp
	$(CPP) $(CFLAGS) analyzer.cpp analyzer.h -std=c++11 -lpcap -pthread -O3 -o $@

clean:
	rm -rf analyzer
