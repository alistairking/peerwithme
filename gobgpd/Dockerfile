FROM peerwithme-gobgp
LABEL maintainer="Alistair King <alistair@kentik.com>"

COPY gobgpd.yaml /usr/local/etc/
ENTRYPOINT ["gobgpd", "--pprof-disable", "--api-hosts", ":50090",  "-f", "/usr/local/etc/gobgpd.yaml"]
