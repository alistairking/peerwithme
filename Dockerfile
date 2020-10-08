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

RUN cp /root/gobgpd /root/gobgp /usr/local/bin/

COPY gobgpd.yaml /usr/local/etc/
COPY proxy.py /usr/local/bin/

ENTRYPOINT ["gobgpd",  "-f", "/usr/local/etc/gobgpd.yaml"]

# proxy.py is not automatically executed. just
# docker exec peerwithme proxy.py
# or, interactively
# docker exec peerwithme bash
# proxy.py