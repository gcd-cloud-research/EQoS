import os
import json

from flask import Flask, request, abort
from werkzeug.utils import secure_filename
import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException

with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as fh:
    token = fh.read()

app = Flask(__name__)
config.load_incluster_config()
kube_api = client.BatchV1Api()


@app.route('/test')
def test():
    return ''


def create_job(routine_id):
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
                    image=routine_id,
                    command=["wrapper.py", routine_id]
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
    if os.fork() == 0:
        os.execl('./buildRoutine.sh', './buildRoutine.sh', routine_id)
    os.wait()

    # Submit job
    job = create_job(routine_id)
    try:
        res = kube_api.create_namespaced_job('default', job, pretty=True)
        app.logger.debug(res)
    except ApiException as exception:
        app.logger.error("Could not create job: %s" % exception)
        abort(500)


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
    create_routine(name)
    return ''


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
