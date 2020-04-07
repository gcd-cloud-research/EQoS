FROM alpine:latest

RUN apk add R R-dev python3 py-pip
WORKDIR /
COPY requirements.txt /
RUN pip install -r requirements.txt
COPY *.py *.r /
ENTRYPOINT ["python"]
