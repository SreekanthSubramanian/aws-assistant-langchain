FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim as final
WORKDIR /app

RUN apt update && \
apt install -y unzip curl && \
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
unzip awscliv2.zip && \
./aws/install && \
rm awscliv2.zip


COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

COPY . .
EXPOSE 8000
CMD [ "python3", "serve.py" ]