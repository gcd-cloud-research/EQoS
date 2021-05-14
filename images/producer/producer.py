import os
import json
import shutil
import time

from flask import Flask, request, abort
from werkzeug.utils import secure_filename
import requests
import docker
import pika

import logging
logging.basicConfig(level=logging.DEBUG)

with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as fh:
    token = fh.read()

registry = os.environ['REGISTRY']

# Create Flask app
app = Flask(__name__)

# Create Docker client
docker_api = docker.from_env()

# Prepare pipe for sending new routines
rpipe, wpipe = os.pipe()

ROUTINE_URL = 'http://mongoapi:8000/routine/'


class Requirements:
    def __init__(self):
        self.req = {}

    def parse_requirements(self, folder, file='requirements.txt'):
        # Does not check for existing file, propagating error is the intended behaviour
        with open('%s/%s' % (folder, file)) as fh:
            for line in fh:
                self.req[line.split('=')[0].strip()] = line.split('=')[-1].strip()
        return self

    def write_requirements(self, folder, file='requirements.txt'):
        with open('%s/%s' % (folder, file), 'w+') as fh:
            for key, value in self.req.items():
                fh.write('%s==%s\n' % (key, value))


@app.route('/test')
def test():
    return ''


def build_and_push(rid, extension):
    """Prepare a new routine, build it and push it."""
    os.chdir('/received')

    # Create new routine folder
    routine_dir = '%sdir' % rid
    shutil.copytree('/routine', routine_dir)

    # Move submitted script to routine folder, changing name but keeping extension
    filename = '%s.%s' % (rid, extension)
    shutil.move('%s/%s' % (rid, filename), '%s/worker.%s' % (routine_dir, extension))

    # Update requirements.txt
    requirements = Requirements()
    if 'requirements.txt' in os.listdir(rid):
        requirements.parse_requirements(rid)
    requirements.parse_requirements(routine_dir)
    shutil.rmtree(rid)
    requirements.write_requirements(routine_dir)

    # Build and push image
    image_tag = '%s/%s' % (registry, rid)
    docker_api.images.build(path=routine_dir, tag=image_tag)
    docker_api.images.push(image_tag)

    res = None
    while not res:
        try:
            res = requests.post(ROUTINE_URL, {'status': 'BUILT'})
        except requests.exceptions.ConnectionError:
            logging.info("Status update failed")

    # Cleanup
    docker_api.images.remove(image=image_tag)
    shutil.rmtree(routine_dir)

    os.chdir('/')


def create_routine(routine_id, extension):
    logging.info("Routine ID: " % routine_id)
    # Build Docker image for routine and upload to registry
    build_and_push(routine_id, extension)

    # Submit job for creation
    conn = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    chan = conn.channel()
    chan.basic_publish(
        exchange='',
        routing_key='jobs',
        body='%s|%s' % (routine_id, extension)
    )
    conn.close()


def initialise_in_db(routine_name):
    # Initialise routine in database
    res = requests.post(ROUTINE_URL + 'new', data=json.dumps({
        'name': routine_name,
        'issuer': '?'
    }))
    if res.status_code != 200:
        app.logger.error("Error submitting routine to database: " + res.text)
        abort(500)
    return res.json()['id']  # Will represent the job in the database and the image


def routine_watcher(reader):
    readfh = os.fdopen(reader)
    while True:
        name = readfh.readline().strip()
        if name != '':
            rid, extension = name.split('.')
            create_routine(rid, extension)
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

    rid = initialise_in_db(name)
    filename = '%s.%s' % (rid, extension)
    os.makedirs('/received/' + rid)

    if 'requirements' in request.files:
        req = request.files['requirements']
        if secure_filename(req.filename).split('.')[-1] != 'txt':
            abort(400)
        req.save('/received/%s/requirements.txt' % rid)

    f.save('/received/%s/%s' % (rid, filename))
    os.write(wpipe, ('%s\n' % filename).encode('utf-8'))
    return {'id': rid}


if __name__ == '__main__':
    if os.fork() == 0:
        os.close(wpipe)
        while True:  # Creates a routine watcher and monitors it, creating another one if it crashes
            if os.fork() == 0:
                routine_watcher(rpipe)
            else:
                code = os.wait()
                app.logger.error("Routine watcher %d exited with code %d" % code)
    else:
        os.close(rpipe)
        app.run(debug=True, host='0.0.0.0')
