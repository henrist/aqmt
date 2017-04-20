CPP=g++

all: analyzer

analyzer: analyzer.cpp
	$(CPP) analyzer.cpp analyzer.h -std=c++11 -lpcap -pthread -O3 -o $@

clean:
	rm -rf analyzer

#libta:
#

#analyzer: analyzer.cpp


