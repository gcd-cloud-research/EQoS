import os
import json
import shutil
import time

from flask import Flask, request, abort
from werkzeug.utils import secure_filename
import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import docker

with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as fh:
    token = fh.read()

registry = os.environ['REGISTRY']

# Create Flask app
app = Flask(__name__)

# Create Kubernetes client
config.load_incluster_config()
kube_api = client.BatchV1Api()

# Create Docker client
docker_api = docker.from_env()

# Prepare pipe for sending new routines
rpipe, wpipe = os.pipe()


@app.route('/test')
def test():
    return ''


def build_and_push(rid, name):
    """Prepare a new routine, build it and push it."""
    os.chdir('/received')

    # Create new routine folder
    routine_dir = '%sdir' % rid
    shutil.copytree('/routine', routine_dir)

    # Move submitted script to routine folder, changing name but keeping extension
    extension = name.split('.')[-1]
    shutil.move(name, '%s/worker.%s' % (routine_dir, extension))

    # Build and push image
    image_tag = '%s/%s' % (registry, rid)
    docker_api.images.build(path=routine_dir, tag=image_tag)
    docker_api.images.push(image_tag)

    # Cleanup
    docker_api.images.remove(image=image_tag)
    shutil.rmtree(routine_dir)

    os.chdir('/')


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


def create_routine(routine_name):
    # Initialise routine in database
    res = requests.post('http://mongoapi:8000/routine/new', data=json.dumps({
        'name': routine_name,
        'issuer': '?'
    }))
    if res.status_code != 200:
        app.logger.error("Error submitting routine to database: " + res.text)
        abort(500)
    routine_id = res.json()['id']  # Will represent the job in the database and the image

    # Build Docker image for routine and upload to registry
    build_and_push(routine_id, routine_name)

    # Submit job
    job = create_job(routine_id, routine_name.split('.')[-1])
    try:
        res = kube_api.create_namespaced_job('default', job, pretty=True)
        app.logger.debug(res)
    except ApiException as exception:
        app.logger.error("Could not create job: %s" % exception)
        abort(500)


def routine_watcher(reader):
    readfh = os.fdopen(reader)
    while True:
        name = readfh.readline().strip()
        if name != '':
            create_routine(name)
        else:
            time.sleep(1)


@app.route('/', methods=['POST'])
def new_routine():
    if 'program' not in request.files:
        abort(400)

    f = request.files['program']
    name = secure_filename(f.filename)
    extension = name.split('.')[-1]
    if extension not in ['py', 'r']:
        abort(400)

    f.save('/received/' + name)
    os.write(wpipe, ('%s\n' % name).encode('utf-8'))
    return ''


if __name__ == '__main__':
    if os.fork() == 0:
        os.close(wpipe)
        routine_watcher(rpipe)
    else:
        os.close(rpipe)
        app.run(debug=True, host='0.0.0.0')
