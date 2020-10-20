FROM caida/bgpstream
LABEL maintainer="Alistair King <alistair@kentik.com>"

RUN \
  apt-get update && \
  apt-get install -y \
    wget \
    python3-pip \
    supervisor

# RUN pip3 install

WORKDIR /root
RUN wget https://github.com/osrg/gobgp/releases/download/v2.20.0/gobgp_2.20.0_linux_amd64.tar.gz && \
  tar zxf gobgp_2.20.0_linux_amd64.tar.gz

RUN cp /root/gobgpd /usr/local/bin/

COPY gobgpd.yaml /usr/local/etc/
COPY proxy.py /usr/local/bin/
COPY gobgp-wrap.sh /usr/local/bin/gobgp

ENTRYPOINT ["gobgpd", "--pprof-disable", "--api-hosts", ":50090",  "-f", "/usr/local/etc/gobgpd.yaml"]

# proxy.py is not automatically executed. just
# docker exec -it peerwithme proxy.py
# or, interactively
# docker exec -it peerwithme bash
# proxy.py
