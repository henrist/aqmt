# set CPATH if missing
CPATH?=$(PWD)/common
export CPATH

all: aqmt
	@echo "---"
	@echo "If you want to use Docker as well, also do 'make aqmt_docker'"
	@echo "See https://github.com/henrist/aqmt-example if you want to"
	@echo "use Docker, as it makes this Makefile obsolete"

aqmt_docker:
	cd docker && make

aqmt:
	cd aqmt && make
	cd aqmt/ta && make

clean:
	cd aqmt && make clean
	cd aqmt/ta && make clean

.PHONY: aqmt
