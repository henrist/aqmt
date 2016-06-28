SRC= analysis.cpp
HEADERS=ipdefs.h analysis.h
CPP=g++
AR=ar

UNAME := $(shell uname)

all: ta

ifeq ($(UNAME), Linux)
CPP=g++
endif

ifeq ($(UNAME), Darwin)
CPP=clang++
endif

libta: $(SRC) $(HEADERS) Makefile
	$(CPP) -c $(SRC) -std=c++11 -O3 -o libta.o
	$(AR) rcs libta.a libta.o
ta: main.cpp $(HEADERS) Makefile libta
	$(CPP) main.cpp -L. -lta -std=c++11 -lpcap -pthread -O3 -o $@
debug: $(SRC) $(HEADERS) Makefile
	$(CPP) -g $(SRC) -std=c++11 -lpcap -pthread -O0 -o $@

####################################################################
####################################################################
####################################################################

clean:
	rm -rf ta debug *~
