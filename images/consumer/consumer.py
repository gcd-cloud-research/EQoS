import json
import os
import time

import pika
import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

config.load_incluster_config()
kube_api = client.BatchV1Api()

conn = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
chan = conn.channel()
chan.queue_declare(queue='jobs', durable=True)

registry = os.environ['REGISTRY']
LOAD_URL = 'http://qos:8000/sysload'
STATUS_URL = 'http://mongoapi:8000/routine/'


def change_job_status(rid, st):
    res = None
    while not res:
        try:
            logging.debug("Changing task status")
            res = requests.post(STATUS_URL + rid, json.dumps({'status': st}))
            logging.debug("Request done: %s" % res)
        except requests.exceptions.ConnectionError:
            logging.error("Status update failed")

    if res.status_code != 200:
        logging.warning("Could not change job status: %s" % res.text)
    else:
        logging.info('Status changed to %s' % st)


def can_create_job():
    try:
        res = requests.get(LOAD_URL)
    except requests.ConnectionError:
        return False
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
    f = open("acklog.txt", "a+")
    f.write("ACK: %s \n" % routine_id)
    f.close()

    if can_create_job():
        logging.info("LoadBalancer allows creation. Starting")
        job = create_job(routine_id, extension)
        try:
            res = kube_api.create_namespaced_job('default', job)
            logging.info("Created")
            logging.debug(res)
            # I think it's ACKing the job, failing on the job status change and then ACKing again and exploding out of the planet
            channel.basic_ack(delivery_tag=method.delivery_tag)
            change_job_status(routine_id, 'QUEUED')
        except ApiException as exception:
            logging.error("Could not create job: %s" % exception)
    else:
        try:
            logging.info("LoadBalancer did not approve. Not creating job")
            change_job_status(routine_id, 'HOLD')
            channel.basic_nack(method.delivery_tag)
            time.sleep(10)
        except Exception as e:
            logging.error(e)


if __name__ == '__main__':
    while True:
        if os.fork() == 0:
            chan.basic_consume(
                queue='jobs',
                on_message_callback=callback
            )
            chan.start_consuming()
        else:
            os.wait()
