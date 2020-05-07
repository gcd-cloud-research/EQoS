import os
import json
import shutil
import time

from flask import Flask, request, abort
from werkzeug.utils import secure_filename
import requests
import docker
import pika

with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as fh:
    token = fh.read()

registry = os.environ['REGISTRY']

# Create Flask app
app = Flask(__name__)

# Create Docker client
docker_api = docker.from_env()

# Prepare pipe for sending new routines
rpipe, wpipe = os.pipe()


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


def build_and_push(rid, name):
    """Prepare a new routine, build it and push it."""
    os.chdir('/received')

    # Create new routine folder
    routine_dir = '%sdir' % rid
    shutil.copytree('/routine', routine_dir)

    # Move submitted script to routine folder, changing name but keeping extension
    name_wo_extension = '.'.join(name.split('.')[:-1])
    extension = name.split('.')[-1]
    shutil.move('%s/%s' % (name_wo_extension, name), '%s/worker.%s' % (routine_dir, extension))

    # Update requirements.txt
    requirements = Requirements()
    if 'requirements.txt' in os.listdir(name_wo_extension):
        requirements.parse_requirements(name_wo_extension)
    requirements.parse_requirements(routine_dir)
    shutil.rmtree(name_wo_extension)
    requirements.write_requirements(routine_dir)

    # Build and push image
    image_tag = '%s/%s' % (registry, rid)
    docker_api.images.build(path=routine_dir, tag=image_tag)
    docker_api.images.push(image_tag)

    # Cleanup
    docker_api.images.remove(image=image_tag)
    shutil.rmtree(routine_dir)

    os.chdir('/')


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

    # Submit job for creation
    conn = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    chan = conn.channel()
    chan.basic_publish(
        exchange='',
        routing_key='jobs',
        body='%s|%s' % (routine_id, routine_name.split('.')[-1])
    )
    conn.close()



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
    name_wo_extension = '.'.join(name.split('.')[:-1])
    if name.split('.')[-1] not in ['py', 'r']:
        abort(400)

    os.makedirs('/received/' + name_wo_extension)

    if 'requirements' in request.files:
        req = request.files['requirements']
        if secure_filename(req.filename).split('.')[-1] != 'txt':
            abort(400)
        req.save('/received/%s/requirements.txt' % name_wo_extension)

    f.save('/received/%s/%s' % (name_wo_extension, name))
    os.write(wpipe, ('%s\n' % name).encode('utf-8'))
    return ''


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
