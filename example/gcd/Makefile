all: docker

docker:
	docker build -t darjeeling/example:gcd docker

check: docker
	darjeeling repair repair.yml

.PHONY: docker check
