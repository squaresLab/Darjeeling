FROM ubuntu:18.04
ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
RUN apt-get update \
 && apt-get install -y \
      git \
      python3 \
      python3-pip \
      sudo \
 && pip3 install \
      coverage \
      pytest \
      pytest-cov \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/flask
RUN git clone https://github.com/pallets/flask /opt/flask \
 && git checkout 38eb5d3b49d628785a470e2e773fc5ac82e3c8e4
COPY config.bad.py /opt/flask/src/flask/config.py
RUN pip3 install -e .
