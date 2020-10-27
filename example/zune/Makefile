all: docker

docker:
	docker build -t darjeeling/example:zune docker

check:
	darjeeling repair repair.yml

.PHONY: docker check
