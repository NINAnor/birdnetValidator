FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

ADD src/ /app/src
ADD assets/ /app/assets
COPY entrypoint.sh /app/

# Create mount point
RUN mkdir -p /data

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
