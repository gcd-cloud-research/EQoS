FROM python:3.7

RUN mkdir /received
WORKDIR /
COPY routine /routine
COPY requirements.txt /
RUN pip install -r requirements.txt
COPY producer.py /
COPY buildRoutine.sh /
CMD ["python", "producer.py"]
