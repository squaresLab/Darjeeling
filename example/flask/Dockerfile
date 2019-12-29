FROM ubuntu:18.04
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
      pytest-cov

WORKDIR /opt/flask
RUN git clone https://github.com/pallets/flask /opt/flask
COPY bug.diff /opt/flask
RUN git apply bug.diff \
 && pip3 install -e .
