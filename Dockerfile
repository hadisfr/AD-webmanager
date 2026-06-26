FROM ubuntu:noble

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update && \
    apt-get -y install --no-install-recommends tzdata unzip build-essential libldap2-dev libsasl2-dev tox lcov valgrind && \
    apt-get -y install --no-install-recommends python3-pip python3-venv python3-dev libjpeg-dev zlib1g-dev && \
    apt-get -y install --no-install-recommends slapd ldap-utils && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./ /

RUN pip3 install --no-cache-dir --break-system-packages wheel
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

EXPOSE 8080

CMD ["python3","ADwebmanager.py"]
