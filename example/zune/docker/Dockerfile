FROM ubuntu:22.04
ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      gcc \
      gcovr \
      libc6-dev \
      patch \
      sudo \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /experiment
COPY zune.c /experiment/source/
COPY test.sh /experiment
COPY test /experiment/test
