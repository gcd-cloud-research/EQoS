import machinestats
from flask import Flask, request, abort
from werkzeug.utils import secure_filename
import time as t

app = Flask(__name__)

@app.route('/test')
def test():
    return "The service is up\n"


@app.route('/stats')
def stats():
    time, cpu, mem = machinestats.get_usage()
    return {
        'time': time,
        'cpu': cpu,
        'mem': mem
    }


@app.route('/routine/python', methods=['GET', 'POST'])
def new_python():
    if request.method == 'POST':
        if 'program' not in request.files:
            abort(400)

        f = request.files['program']
        name = secure_filename(f.filename)
        if name.split('.')[-1] != 'py':
            abort(401)

        f.save('/received/' + name)
        return 'OK'

    return 'Submit a python script file with name "program"'

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
