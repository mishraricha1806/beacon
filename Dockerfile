FROM python:3.12-slim AS builder

WORKDIR /src

COPY pyproject.toml requirements.txt README.md VERSION ./
COPY beacon ./beacon
COPY packs ./packs
COPY scripts ./scripts

RUN apt-get update \
    && apt-get install -y --no-install-recommends binutils \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt pyinstaller
RUN python scripts/build_binaries.py linux

FROM debian:trixie-slim

LABEL maintainer="beacon-team@company.com"
LABEL description="Beacon - Production-readiness intelligence for distributed systems"

WORKDIR /workspace

COPY --from=builder /src/dist-binaries/beacon-linux /usr/local/bin/beacon
COPY examples ./examples

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN chmod +x /usr/local/bin/beacon

EXPOSE 8765

ENTRYPOINT ["beacon"]
CMD ["--help"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=1 \
  CMD beacon --help >/dev/null || exit 1
