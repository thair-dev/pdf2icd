# Dockerfile for pdf2icd project

############################
# 1. Base – shared tooling #
############################
FROM mcr.microsoft.com/azure-functions/python:4-python3.12 AS base

ENV CACHE_BUSTER="2025-07-24" \
    LC_ALL="C.UTF-8" \
    PATH="/home/.local/bin:$PATH" \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /home/site/wwwroot

# Install build tools and PDF/OCR dependencies
# Poetry is pinned for reproducibility
# en_ner_bc5cdr is installed here for Docker cache efficiency (large download)
RUN apt-get install -y --no-install-recommends \
    curl \
    git \
    gzip \
    poppler-utils \
    ocrmypdf \
    tar \
    tesseract-ocr \
    unpaper \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python - --version 1.8.5 \
    && python -m venv .venv \
    && . .venv/bin/activate \
    && pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz

#############################
# 2. build – app & deps     #
#############################
FROM base AS build

COPY README.md poetry.lock pyproject.toml setup.cfg ./
COPY pdf2icd ./pdf2icd

RUN poetry install --only main

#############################
# 3. test – lint/test suite #
#############################
FROM build AS test
COPY tests ./tests
RUN poetry install \
    && poetry run pytest

###########################################
# 4. final – production Azure container   #
###########################################
FROM build AS final
