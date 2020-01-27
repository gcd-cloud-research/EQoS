import machinestats
from flask import Flask, request, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)


@app.route('/test')
def test():
    return "The service is up"


@app.route('/stats')
def stats():
    time, cpu, mem = machinestats.get_usage()
    return {
        'time': time,
        'cpu': cpu,
        'mem': mem
    }


@app.route('/routine', methods=['GET', 'POST', 'OPTIONS'])
def new_routine():
    if request.method == 'OPTIONS':
        return
    elif request.method == 'POST':
        if 'program' not in request.files:
            abort(400)

        f = request.files['program']
        name = secure_filename(f.filename)
        extension = name.split('.')[-1]
        if extension not in ['py', 'r']:
            abort(400)

        f.save('/received/' + name)
        return

    return 'Submit a python or R script file with name "program"'


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
