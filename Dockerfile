FROM m13253/tornado:wily-3.5
MAINTAINER Star Brilliant <m13253@hotmail.com>

RUN apt-get -y update && \
    apt-get -y install --no-install-recommends gcc-5 g++-5 git make && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/gcc-5 /usr/local/bin/gcc && \
    ln -sf /usr/bin/g++-5 /usr/local/bin/g++

RUN useradd -m user

ADD src /home/user/cibackend

USER user
EXPOSE 8080
WORKDIR /home/user/

ENTRYPOINT /home/user/cibackend/server.py

