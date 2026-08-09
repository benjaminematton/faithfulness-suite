FROM ubuntu:24.04
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx
WORKDIR /app
