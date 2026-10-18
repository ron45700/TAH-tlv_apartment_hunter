# The image of `docs/PHASE_3.md` 3.9 (b) (DECISIONS.md #258: one image, two stages; #416, #424).
# Every base is pinned by its tag and the index digest read on 2026-10-16 from the registry's own
# pages (Docker Hub's tag API, GitHub's package page), never by pulling. Docker checks a digest when
# it pulls, so a wrong one fails the build.

# Stage 1: the site's pages. Node stays in this stage only.
FROM node:24.22.0-trixie-slim@sha256:7f486cabe892bff8fef04c0f7da8dba84a560be3e4e2740b7a86afc57ebec315 AS pages
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: the image. Python's own `sqlite3` is Debian trixie's library (ASSUMPTIONS.md I8).
FROM python:3.12.15-slim-trixie@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
# The locked dependencies only, no dev group. uv is mounted for this one step (Dockerfile 1.2+:
# a bind mount's `from` may be an image), so no uv is left in the image.
RUN --mount=from=ghcr.io/astral-sh/uv:0.12.11@sha256:79c6f4776b851471cc73b7d21d0cc834bb94383c292e83640d27eff512864df7,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=.python-version,target=.python-version \
    uv sync --locked
RUN useradd --system --uid 10001 --user-group --no-create-home app
COPY tlv_hunter/ tlv_hunter/
COPY config/ config/
COPY reference/ reference/
COPY --from=pages /frontend/dist frontend/dist
# The store root is the volume's mount point: a new named volume takes this folder's owner.
RUN mkdir -p data/store data/labeling data/gate_d data/store_exports data/measure \
    && chown -R app:app data
ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000
CMD ["python", "-m", "tlv_hunter.jobs.serve", "--store", "--host", "0.0.0.0"]
