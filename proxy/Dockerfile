FROM peerwithme-gobgp
LABEL maintainer="Alistair King <alistair@kentik.com>"

RUN \
  apt-get update && \
  apt-get install -y \
    wget \
    python3-pip \
    git

RUN pip3 install git+https://github.com/alistairking/PyGoBGP.git@upgrade-gobgp-api

COPY proxy.py /usr/local/bin/

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["proxy.py"]

