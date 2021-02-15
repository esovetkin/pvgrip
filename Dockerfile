FROM mundialis/grass-py3-pdal:stable-ubuntu

RUN apt-get update -y
RUN apt-get install -y \
    python3-pip libspatialindex-dev \
    bc pdal \
    redis git \
    librsvg2-dev libtool

RUN mkdir /code
ADD . /code/
WORKDIR /code

RUN scripts/install_smrender.sh
RUN pip3 install -r requirements.txt
RUN pip3 install -e .

CMD scripts/start_server.sh

EXPOSE 8080
