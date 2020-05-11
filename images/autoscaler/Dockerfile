FROM python:3.7

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY plugins /
COPY pluginmanager.py /
COPY autoscaler.py /
COPY config.json /

CMD ["python", "autoscaler.py"]