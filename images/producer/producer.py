from flask import Flask, request, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)


@app.route('/test')
def test():
    return ''


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
    return ''


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
