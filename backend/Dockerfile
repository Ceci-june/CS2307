FROM python:3.9-slim

RUN ln -snf /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime && echo Asia/Ho_Chi_Minh > /etc/timezone

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
RUN apt-get update

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    libmagic1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libnss3-tools \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libexpat1 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    lsb-release \
    libxshmfence1 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install pip requirements
RUN python -m pip install pip setuptools wheel
COPY . /app
WORKDIR /app

ADD ./requirements.txt requirements.txt
ADD .env .env

RUN pip install -r requirements.txt
RUN playwright install
#RUN pip install h11==0.14.0
# Install opencv dependencies
CMD ["/bin/bash"]
