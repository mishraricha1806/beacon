FROM python:3.11-slim

# Set metadata
LABEL maintainer="beacon-team@company.com"
LABEL description="Beacon - Production-readiness intelligence for distributed systems"

# Set working directory
WORKDIR /app

# Copy requirements and source
COPY requirements.txt .
COPY beacon/ ./beacon/
COPY VERSION .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create entry point
RUN echo '#!/bin/bash\npython3 -m beacon.cli "$@"' > /usr/local/bin/beacon && \
    chmod +x /usr/local/bin/beacon

# Set default command
ENTRYPOINT ["beacon"]
CMD ["--help"]

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=1 \
  CMD beacon --version || exit 1

