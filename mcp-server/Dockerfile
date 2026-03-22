FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# MCP server communicates over stdio — run interactively via `docker compose run mcp`
CMD ["python", "server.py"]
