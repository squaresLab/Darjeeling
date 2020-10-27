FROM ubuntu:16.04
ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

# create docker user
RUN apt-get update \
 && apt-get install --no-install-recommends -y sudo patch \
 && useradd -ms /bin/bash docker \
 && echo 'docker ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
 && adduser docker sudo \
 && apt-get clean \
 && mkdir -p /home/docker \
 && sudo chown -R docker /home/docker \
 && sudo chown -R docker /usr/local/bin \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
USER docker

# install dependencies
RUN sudo apt-get update \
 && sudo apt-get install -y --no-install-recommends \
      gcc \
      gcovr \
      libc6-dev \
 && sudo apt-get clean \
 && sudo rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /experiment
COPY gcd.c /experiment/source/
COPY test.sh /experiment
COPY test /experiment/test
RUN sudo chown -R docker /experiment
