FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Install dependencies
# Copy pyproject.toml and uv.lock first to leverage cache
COPY pyproject.toml uv.lock ./

# Install dependencies into the system python environment
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
