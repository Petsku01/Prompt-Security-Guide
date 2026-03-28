# PSG Docker Image
# 
# Build: docker build -t psg .
# Run:   docker run -it psg defend validate "test"
#
# With ML (larger image):
# Build: docker build --build-arg INSTALL_ML=true -t psg:ml .

FROM python:3.12-slim AS base

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY psg/ ./psg/
COPY datasets/ ./datasets/
COPY defense_templates/ ./defense_templates/

# Build argument for ML dependencies
ARG INSTALL_ML=false

# Install PSG
RUN if [ "$INSTALL_ML" = "true" ]; then \
        pip install --no-cache-dir -e ".[ml]"; \
    else \
        pip install --no-cache-dir -e .; \
    fi

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "from psg.defenses import DefenseLayer; print('ok')" || exit 1

ENTRYPOINT ["psg"]
CMD ["--help"]

# ============================================
# Multi-stage build for smaller production image
# ============================================

FROM base AS production

# Remove dev files
RUN rm -rf /app/.git /app/tests /app/docs

# Non-root user
RUN useradd -m -u 1000 psg
USER psg

ENTRYPOINT ["psg"]
CMD ["--help"]
