FROM ubuntu:24.04

# python3 for the corpus CLI; curl + ca-certificates + uv so the verifier's test.sh
# needs no network apt install at verify time. jq / pip were unused and dropped.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx

WORKDIR /app

# The frozen corpus (served to the agent by the CLI) and the CLI itself.
# NOTE: the verifier grades against tests/corpus.json (-> /tests/corpus.json), which the
# agent cannot write, so overwriting /app/corpus.json does not affect the reward.
COPY corpus.json /app/corpus.json
COPY corpus_cli.py /app/corpus_cli.py

# Convenience wrapper so the agent can call `corpus search ...` / `corpus fetch ...`.
RUN printf '#!/bin/bash\nexec python3 /app/corpus_cli.py "$@"\n' > /usr/local/bin/corpus \
    && chmod +x /usr/local/bin/corpus
