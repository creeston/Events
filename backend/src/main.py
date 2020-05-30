import sys

sys.path.append("../")
sys.path.append(".")

from models import Event
from flask import Flask, jsonify, request, _request_ctx_stack
from sql_storage import EventRepository
from datetime import datetime
from flask_cors import CORS
from .auth import requires_auth, AuthError

app = Flask(__name__)
CORS(app)


@app.route('/events', methods=['POST'])
@requires_auth
def get_events():
    content = request.json
    date = datetime(year=content['year'], day=content['day'], month=content['month'])
    username = _request_ctx_stack.top.current_user['sub']
    with EventRepository() as repository:
        events = repository.list_events_by_date_for_user(date, username)

    return jsonify([e.to_json() for e in events])


@app.route('/events/exclude', methods=['POST'])
@requires_auth
def exclude_event():
    content = request.json
    event_id = int(content['event_id'])
    username = _request_ctx_stack.top.current_user['sub']
    with EventRepository() as repository:
        repository.exclude_event(event_id, username, 0)

    resp = jsonify(success=True)
    return resp


@app.route('/events/modify', methods=['POST'])
@requires_auth
def modify_event():
    req_json = request.json
    event_json = req_json[0]
    original_json = req_json[1]
    username = _request_ctx_stack.top.current_user['sub']
    with EventRepository() as repository:
        event_id, source_event_id = repository.update_event(
            Event.from_json(event_json),
            Event.from_json(original_json),
            username
        )
        repository.exclude_event(source_event_id, username, 1)

    resp = jsonify({"event_id": int(event_id), "source_event_id": int(source_event_id)})
    return resp


@app.route('/events/duplicate', methods=['POST'])
@requires_auth
def report_duplicated_events():
    req_json = request.json
    events = [Event.from_json(j) for j in req_json]
    username = _request_ctx_stack.top.current_user['sub']
    with EventRepository() as repository:
        repository.mark_events_as_duplicate(events, username)

    resp = jsonify(success=True)
    return resp


@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


if __name__ == "__main__":
    app.run()
