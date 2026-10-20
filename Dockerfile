FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 AS builder

WORKDIR /src

COPY pyproject.toml requirements.txt requirements.lock requirements-dev.lock README.md VERSION ./
COPY beacon ./beacon
COPY packs ./packs
COPY scripts ./scripts

RUN apt-get update \
    && apt-get install -y --no-install-recommends binutils \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.lock -r requirements-dev.lock
RUN python scripts/build_binaries.py linux

FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f

LABEL maintainer="beacon-team@company.com"
LABEL description="Beacon - Production-readiness intelligence for distributed systems"

WORKDIR /workspace

COPY --from=builder /src/dist-binaries/beacon-linux /usr/local/bin/beacon
COPY examples ./examples

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 beacon \
    && useradd --uid 10001 --gid beacon --no-create-home --shell /usr/sbin/nologin beacon \
    && chmod +x /usr/local/bin/beacon \
    && chown -R beacon:beacon /workspace

USER 10001:10001

EXPOSE 8765

ENTRYPOINT ["beacon"]
CMD ["--help"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=1 \
  CMD beacon --help >/dev/null || exit 1
