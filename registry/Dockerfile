FROM mambaorg/micromamba:2.5.0 AS base

USER root
ARG MAMBA_USER_ID=57439
ARG MAMBA_USER_GID=57439

# Install system dependencies (if needed for scientific libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER $MAMBA_USER
WORKDIR /app

COPY --chown=$MAMBA_USER:$MAMBA_USER env.yml ./env.yml
RUN micromamba install -y -n base -f ./env.yml && \
    micromamba clean --all --yes
# Excute RUN commands with activated conda environment
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Install Python dependencies if a requirements file exists
COPY --chown=$MAMBA_USER:$MAMBA_USER requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir -r requirements.txt

COPY --chown=$MAMBA_USER:$MAMBA_USER . .

CMD ["python", "registry.py", "--help"]
