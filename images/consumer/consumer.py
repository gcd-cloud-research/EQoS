import os
import time

import pika
import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import requests

logging.basicConfig(level=logging.INFO)

config.load_incluster_config()
kube_api = client.BatchV1Api()

conn = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
chan = conn.channel()
chan.queue_declare(queue='jobs', durable=True)

registry = os.environ['REGISTRY']
LOAD_URL = 'http://qos:8000/sysload'
STATUS_URL = 'http://mongoapi:8000/routine/'


def can_create_job():
    from datetime import datetime
    res = requests.get(LOAD_URL)
    logging.info('%s - %s' % (datetime.now().isoformat(), res.text))
    return res.status_code == 200 and res.json()['status']


def create_job(routine_id, extension):
    """Fill job as per routine.yaml content."""
    # Create job base object
    job = client.V1Job(api_version='batch/v1', kind='Job')
    # Fill with metadata
    job.metadata = client.V1ObjectMeta(name=routine_id)
    # Prepare template object
    job.spec = client.V1JobSpec(
        template=client.V1PodTemplateSpec(
            spec=client.V1PodSpec(
                containers=[client.V1Container(
                    name=routine_id,
                    image="%s/%s" % (registry, routine_id),
                    args=["wrapper.py", routine_id, extension]
                )],
                restart_policy='Never'
            )
        ),
        backoff_limit=4
    )
    return job


def callback(channel, method, properties, body):
    body = body.decode('utf-8')
    routine_id, extension = "|".join(body.split("|")[:-1]), body.split("|")[-1]
    logging.info("Received id %s, extension %s" % (routine_id, extension))
    if can_create_job():
        logging.info("LoadBalancer allows creation. Starting")
        job = create_job(routine_id, extension)
        try:
            res = kube_api.create_namespaced_job('default', job)
            logging.info("Created")
            logging.debug(res)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            requests.post(STATUS_URL + routine_id, {'status': 'QUEUED'})
        except ApiException as exception:
            logging.error("Could not create job: %s" % exception)
    else:
        logging.info("LoadBalancer did not approve. Not creating job")
        requests.post(STATUS_URL + routine_id, {'status': 'HELD'})
        time.sleep(10)


if __name__ == '__main__':
    chan.basic_consume(
        queue='jobs',
        on_message_callback=callback
    )
    chan.start_consuming()
