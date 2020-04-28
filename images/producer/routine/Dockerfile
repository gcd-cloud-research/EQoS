FROM alpine:latest

RUN apk add R R-dev python3 py-pip
RUN pip3 install --upgrade pip
ENV PYTHONPATH '/usr/local/lib/python3.7/site-packages'
WORKDIR /
COPY requirements.txt /
RUN pip3 install -r requirements.txt
COPY *.py *.r /
ENTRYPOINT ["python3"]
