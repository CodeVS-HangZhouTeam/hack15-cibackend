FROM m13253/tornado:wily-3.5
MAINTAINER Star Brilliant <m13253@hotmail.com>

RUN useradd -m user

ADD src /home/user/cibackend

USER user
EXPOSE 8080
WORKDIR /home/user/

ENTRYPOINT /home/user/cibackend/server.py

