all: docker

docker:
	docker build -t squareslab/tse2012:gcd docker

check: docker
	darjeeling repair repair.yml

.PHONY: docker check
