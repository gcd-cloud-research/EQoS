FROM python:3.7

RUN mkdir /received

WORKDIR /

RUN pip install --upgrade pip

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY routine /routine
COPY producer.py /

ENV REGISTRY "192.168.101.76:5000"
ENV DOCKER_HOST "unix:///var/run/docker.sock"

CMD ["python", "producer.py"]
