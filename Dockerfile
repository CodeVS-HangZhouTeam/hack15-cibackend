FROM m13253/tornado:wily-3.5
MAINTAINER Star Brilliant <m13253@hotmail.com>

RUN sed -i 's/archive\.ubuntu\.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list && \
    apt-get -y update && \
    apt-get -y install --no-install-recommends gcc-5 g++-5 git make language-pack-zh-hans && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/gcc-5 /usr/local/bin/cc && \
    ln -sf /usr/bin/g++-5 /usr/local/bin/cxx && \
    ln -sf /usr/bin/gcc-5 /usr/local/bin/gcc && \
    ln -sf /usr/bin/g++-5 /usr/local/bin/g++

RUN useradd -m user

ADD src /home/user/cibackend

USER user
EXPOSE 8080
WORKDIR /home/user/
ENV LANG zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8

ENTRYPOINT /home/user/cibackend/server.py

