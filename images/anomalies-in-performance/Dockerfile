FROM python:3.7

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY detect_anomalies.py /

CMD ["python", "detect_anomalies.py"]