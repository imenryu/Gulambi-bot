FROM python:3.13.2-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev tzdata \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Kolkata
RUN ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && dpkg-reconfigure -f noninteractive tzdata

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python3", "main.py"]
