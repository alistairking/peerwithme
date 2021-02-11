FROM caida/bgpstream
LABEL maintainer="Alistair King <alistair@kentik.com>"

RUN \
  apt-get update && \
  apt-get install -y wget

ARG GOBGPV="2.23.0"
WORKDIR /root
RUN wget https://github.com/osrg/gobgp/releases/download/v${GOBGPV}/gobgp_${GOBGPV}_linux_amd64.tar.gz && \
  tar zxf gobgp_${GOBGPV}_linux_amd64.tar.gz
RUN cp /root/gobgpd /usr/local/bin/

COPY gobgp-wrap.sh /usr/local/bin/gobgp

