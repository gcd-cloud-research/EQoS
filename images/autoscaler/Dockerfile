FROM python:3.7

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY plugins /plugins
COPY autoscaler.py /
COPY config.json /

CMD ["python", "autoscaler.py"]