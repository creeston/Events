import sys
import os

sys.path.append(os.path.abspath("../"))


from flask import Flask, jsonify, request, make_response, _request_ctx_stack
from sql_storage import EventRepository
from datetime import datetime
from flask_cors import CORS
from auth import requires_auth, AuthError

app = Flask(__name__)
CORS(app)


@app.route('/events', methods=['POST'])
@requires_auth
def get_events():
    content = request.json
    date = datetime(year=content['year'], day=content['day'], month=content['month'])
    with EventRepository() as repository:
        events = repository.list_events_by_date(date)

    return jsonify([e.to_json() for e in events])


@app.route('/events/exclude', methods=['POST'])
@requires_auth
def exclude_event():
    content = request.json
    event_id = int(content['event_id'])
    username = _request_ctx_stack.top.current_user['sub']
    with EventRepository() as repository:
        repository.exclude_event(event_id, username)

    resp = jsonify(success=True)
    return resp


@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


if __name__ == "__main__":
    app.run()
