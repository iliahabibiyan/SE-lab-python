# Stage 1: install the dependencies into a virtual environment
FROM python:3.12-slim AS build
WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: the final image has only the virtual environment and the application
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"
COPY --from=build /opt/venv /opt/venv
COPY main.py ./
COPY app ./app
COPY migrations ./migrations
USER 10001:10001
EXPOSE 8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]