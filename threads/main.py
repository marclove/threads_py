import os
import ssl
from functools import wraps
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)

from flask_session import Session

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SESSION_SECRET')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

DEFAULT_THREADS_QUERY_LIMIT = 10

FIELD__ERROR_MESSAGE = 'error_message'
FIELD__FOLLOWERS_COUNT = 'followers_count'
FIELD__HIDE_STATUS = 'hide_status'
FIELD__IS_REPLY = 'is_reply'
FIELD__LIKES = 'likes'
FIELD__MEDIA_TYPE = 'media_type'
FIELD__MEDIA_URL = 'media_url'
FIELD__PERMALINK = 'permalink'
FIELD__REPLIES = 'replies'
FIELD__REPOSTS = 'reposts'
FIELD__QUOTES = 'quotes'
FIELD__REPLY_AUDIENCE = 'reply_audience'
FIELD__STATUS = 'status'
FIELD__TEXT = 'text'
FIELD__TIMESTAMP = 'timestamp'
FIELD__THREADS_BIOGRAPHY = 'threads_biography'
FIELD__THREADS_PROFILE_PICTURE_URL = 'threads_profile_picture_url'
FIELD__USERNAME = 'username'
FIELD__VIEWS = 'views'

MEDIA_TYPE__CAROUSEL = 'CAROUSEL'
MEDIA_TYPE__IMAGE = 'IMAGE'
MEDIA_TYPE__TEXT = 'TEXT'
MEDIA_TYPE__VIDEO = 'VIDEO'

PARAMS__ACCESS_TOKEN = 'access_token'
PARAMS__USER_ID = 'user_id'
PARAMS__CLIENT_ID = 'client_id'
PARAMS__CONFIG = 'config'
PARAMS__FIELDS = 'fields'
PARAMS__HIDE = 'hide'
PARAMS__METRIC = 'metric'
PARAMS__QUOTA_USAGE = 'quota_usage'
PARAMS__REDIRECT_URI = 'redirect_uri'
PARAMS__REPLY_CONFIG = 'reply_config'
PARAMS__REPLY_CONTROL = 'reply_control'
PARAMS__REPLY_QUOTA_USAGE = 'reply_quota_usage'
PARAMS__REPLY_TO_ID = 'reply_to_id'
PARAMS__RESPONSE_TYPE = 'response_type'
PARAMS__RETURN_URL = 'return_url'
PARAMS__SCOPE = 'scope'
PARAMS__TEXT = 'text'

HOST = os.getenv('HOST')
PORT = int(os.getenv('PORT', 5000))
REDIRECT_URI = os.getenv('REDIRECT_URI')
APP_ID = os.getenv('APP_ID')
API_SECRET = os.getenv('API_SECRET')
GRAPH_API_VERSION = os.getenv('GRAPH_API_VERSION')
INITIAL_ACCESS_TOKEN = os.getenv('INITIAL_ACCESS_TOKEN')
INITIAL_USER_ID = os.getenv('INITIAL_USER_ID')

GRAPH_API_BASE_URL = f"https://graph.threads.net/{GRAPH_API_VERSION}/" if GRAPH_API_VERSION else "https://graph.threads.net/"
AUTHORIZATION_BASE_URL = 'https://www.threads.net/'

initial_access_token = INITIAL_ACCESS_TOKEN
initial_user_id = INITIAL_USER_ID

SCOPES = [
    'threads_basic',
    'threads_content_publish',
    'threads_manage_insights',
    'threads_manage_replies',
    'threads_read_replies'
]

def build_graph_api_url(path, params={}, access_token=None, base_url=None):
    base_url = base_url or GRAPH_API_BASE_URL
    url = f"{base_url}{path}"
    if params:
        url += f"?{urlencode(params)}"
    if access_token:
        url += f"&{PARAMS__ACCESS_TOKEN}={access_token}"
    return url

def use_initial_authentication_values():
    global initial_access_token, initial_user_id
    session[PARAMS__ACCESS_TOKEN] = initial_access_token
    session[PARAMS__USER_ID] = initial_user_id
    initial_access_token = None
    initial_user_id = None

def get_insights_value(metrics, index):
    if metrics[index]:
        metrics[index]['value'] = metrics[index].get('values', [{}])[0].get('value')

def get_insights_total_value(metrics, index):
    if metrics[index]:
        metrics[index]['value'] = metrics[index].get('total_value', {}).get('value')

def add_attachment_fields(target, attachment_type, url):
    if attachment_type == 'Image':
        target['media_type'] = MEDIA_TYPE__IMAGE
        target['image_url'] = url
    elif attachment_type == 'Video':
        target['media_type'] = MEDIA_TYPE__VIDEO
        target['video_url'] = url

def set_url_param_if_present(source_url, destination_url, param_name):
    param_value = source_url.query.get(param_name)
    if param_value:
        destination_url[param_name] = param_value

def get_cursor_url_from_graph_api_paging_url(req, graph_api_paging_url):
    graph_url = urlparse(graph_api_paging_url)
    cursor_url = url_for(req.endpoint, _external=True)
    cursor_url = f"{cursor_url}?{urlencode(req.args)}"
    cursor_params = parse_qs(graph_url.query)
    set_url_param_if_present(cursor_params, cursor_url, 'limit')
    set_url_param_if_present(cursor_params, cursor_url, 'before')
    set_url_param_if_present(cursor_params, cursor_url, 'after')
    return cursor_url

def logged_in_user_checker(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get(PARAMS__ACCESS_TOKEN) and session.get(PARAMS__USER_ID):
            return f(*args, **kwargs)
        elif initial_access_token and initial_user_id:
            use_initial_authentication_values()
            return f(*args, **kwargs)
        else:
            return redirect(f"/?{PARAMS__RETURN_URL}={request.url}")
    return wrapper

@app.route('/')
def index():
    if not (session.get(PARAMS__ACCESS_TOKEN) or session.get(PARAMS__USER_ID)) and (initial_access_token and initial_user_id):
        use_initial_authentication_values()
        return redirect(url_for('account'))
    return render_template('index.jinja2', title='Index', returnUrl=request.args.get(PARAMS__RETURN_URL))

@app.route('/login')
def login():
    url = build_graph_api_url('oauth/authorize', {
        PARAMS__SCOPE: ','.join(SCOPES),
        PARAMS__CLIENT_ID: APP_ID,
        PARAMS__REDIRECT_URI: REDIRECT_URI,
        PARAMS__RESPONSE_TYPE: 'code',
    }, base_url=AUTHORIZATION_BASE_URL)
    return redirect(url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    uri = build_graph_api_url('oauth/access_token', {}, base_url=GRAPH_API_BASE_URL)
    try:
        response = requests.post(uri, data={
            'client_id': APP_ID,
            'client_secret': API_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'code': code,
        }, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        data = response.json()
        session[PARAMS__ACCESS_TOKEN] = data['access_token']
        session[PARAMS__USER_ID] = data['user_id']
        return redirect(url_for('account'))
    except Exception as e:
        return render_template('index.jinja2', error=f'There was an error with the request: {e}')

@app.route('/account')
@logged_in_user_checker
def account():
    url = build_graph_api_url('me', {
        PARAMS__FIELDS: ','.join([FIELD__USERNAME, FIELD__THREADS_PROFILE_PICTURE_URL, FIELD__THREADS_BIOGRAPHY])
    }, session[PARAMS__ACCESS_TOKEN])
    user_details = {}
    try:
        response = requests.get(url)
        user_details = response.json()
        user_details['user_profile_url'] = f"https://www.threads.net/@{user_details['username']}"
    except Exception as e:
        print(e)
    return render_template('account.jinja2', title='Account', **user_details)

@app.route('/userInsights')
@logged_in_user_checker
def user_insights():
    since = request.args.get('since')
    until = request.args.get('until')
    params = {
        PARAMS__METRIC: ','.join([
            FIELD__VIEWS, FIELD__LIKES, FIELD__REPLIES, FIELD__QUOTES, FIELD__REPOSTS, FIELD__FOLLOWERS_COUNT
        ])
    }
    if since:
        params['since'] = since
    if until:
        params['until'] = until

    url = build_graph_api_url(f"{session[PARAMS__USER_ID]}/threads_insights", params, session[PARAMS__ACCESS_TOKEN])
    metrics = []
    try:
        response = requests.get(url)
        data = response.json()
        metrics = data.get('data', [])
    except Exception as e:
        print(e)

    for index in range(len(metrics)):
        metric = metrics[index]
        if metric['name'] == FIELD__VIEWS:
            get_insights_value(metrics, index)
        else:
            get_insights_total_value(metrics, index)

    return render_template('user_insights.jinja2', title='User Insights', metrics=metrics, since=since, until=until)

@app.route('/publishingLimit')
@logged_in_user_checker
def publishing_limit():
    params = {
        PARAMS__FIELDS: ','.join([
            PARAMS__QUOTA_USAGE, PARAMS__CONFIG, PARAMS__REPLY_QUOTA_USAGE, PARAMS__REPLY_CONFIG
        ])
    }
    url = build_graph_api_url(f"{session[PARAMS__USER_ID]}/threads_publishing_limit", params, session[PARAMS__ACCESS_TOKEN])
    data = {}
    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print(e)

    data = data.get('data', [{}])[0]
    quota_usage = data.get(PARAMS__QUOTA_USAGE)
    config = data.get(PARAMS__CONFIG)
    reply_quota_usage = data.get(PARAMS__REPLY_QUOTA_USAGE)
    reply_config = data.get(PARAMS__REPLY_CONFIG)

    return render_template('publishing_limit.jinja2', title='Publishing Limit', quotaUsage=quota_usage, config=config, replyQuotaUsage=reply_quota_usage, replyConfig=reply_config)

@app.route('/upload')
@logged_in_user_checker
def upload():
    reply_to_id = request.args.get('replyToId', '')
    title = 'Upload' if reply_to_id == '' else 'Upload (Reply)'
    return render_template('upload.jinja2', title=title, replyToId=reply_to_id)

@app.route('/upload', methods=['POST'])
@logged_in_user_checker
def handle_upload():
    text = request.form.get('text')
    attachment_type = request.form.getlist('attachmentType[]')
    attachment_url = request.form.getlist('attachmentUrl[]')
    reply_control = request.form.get('replyControl')
    reply_to_id = request.form.get('replyToId')

    params: dict[str, Any] = {
        PARAMS__TEXT: text,
        PARAMS__REPLY_CONTROL: reply_control,
        PARAMS__REPLY_TO_ID: reply_to_id,
    }

    if not attachment_type:
        params['media_type'] = MEDIA_TYPE__TEXT
    elif len(attachment_type) == 1:
        add_attachment_fields(params, attachment_type[0], attachment_url[0])
    else:
        params['media_type'] = MEDIA_TYPE__CAROUSEL
        params['children'] = []
        for i, type in enumerate(attachment_type):
            child = {'is_carousel_item': True}
            add_attachment_fields(child, type, attachment_url[i])
            params['children'].append(child)

    if params['media_type'] == MEDIA_TYPE__CAROUSEL:
        create_child_promises = [requests.post(build_graph_api_url(f"{session[PARAMS__USER_ID]}/threads", child, session[PARAMS__ACCESS_TOKEN])) for child in params['children']]
        try:
            responses = [promise.json() for promise in create_child_promises]
            params['children'] = ','.join([response['id'] for response in responses if 'id' in response])
        except Exception as e:
            return jsonify({'error': True, 'message': f"Error creating child elements: {e}"}), 500

    url = build_graph_api_url(f"{session[PARAMS__USER_ID]}/threads", params, session[PARAMS__ACCESS_TOKEN])

    try:
        response = requests.post(url)
        data = response.json()
        return jsonify({'id': data['id']})
    except Exception as e:
        return jsonify({'error': True, 'message': f"Error during upload: {e}"}), 500

@app.route('/publish/<container_id>')
@logged_in_user_checker
def publish(container_id):
    return render_template('publish.jinja2', containerId=container_id, title='Publish')

@app.route('/container/status/<container_id>')
@logged_in_user_checker
def container_status(container_id):
    url = build_graph_api_url(container_id, {
        PARAMS__FIELDS: ','.join([FIELD__STATUS, FIELD__ERROR_MESSAGE])
    }, session[PARAMS__ACCESS_TOKEN])
    try:
        response = requests.get(url)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': True, 'message': f"Error querying container status: {e}"}), 500

@app.route('/publish', methods=['POST'])
@logged_in_user_checker
def handle_publish():
    container_id = request.form.get('containerId')
    url = build_graph_api_url(f"{session[PARAMS__USER_ID]}/threads_publish", {'creation_id': container_id}, session[PARAMS__ACCESS_TOKEN])
    try:
        response = requests.post(url)
        data = response.json()
        return jsonify({'id': data['id']})
    except Exception as e:
        return jsonify({'error': True, 'message': f"Error during publishing: {e}"}), 500

@app.route('/threads/<thread_id>')
@logged_in_user_checker
def thread(thread_id):
    url = build_graph_api_url(thread_id, {
        PARAMS__FIELDS: ','.join([
            FIELD__TEXT, FIELD__MEDIA_TYPE, FIELD__MEDIA_URL, FIELD__PERMALINK, FIELD__TIMESTAMP, FIELD__IS_REPLY, FIELD__USERNAME, FIELD__REPLY_AUDIENCE
        ])
    }, session[PARAMS__ACCESS_TOKEN])
    data = {}
    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        print(e)
    return render_template('thread.jinja2', threadId=thread_id, **data, title='Thread')

@app.route('/threads')
@logged_in_user_checker
def threads():
    before = request.args.get('before')
    after = request.args.get('after')
    limit = request.args.get('limit')
    params = {
        PARAMS__FIELDS: ','.join([
            FIELD__TEXT, FIELD__MEDIA_TYPE, FIELD__MEDIA_URL, FIELD__PERMALINK, FIELD__TIMESTAMP, FIELD__REPLY_AUDIENCE
        ]),
        'limit': limit or DEFAULT_THREADS_QUERY_LIMIT,
    }
    if before:
        params['before'] = before
    if after:
        params['after'] = after

    url = build_graph_api_url(f"{session[PARAMS__USER_ID]}/threads", params, session[PARAMS__ACCESS_TOKEN])
    threads = []
    paging = {}
    try:
        response = requests.get(url)
        data = response.json()
        threads = data.get('data', [])
        if 'paging' in data:
            paging_data = data['paging']
            if 'next' in paging_data:
                paging['nextUrl'] = get_cursor_url_from_graph_api_paging_url(request, paging_data['next'])
            if 'previous' in paging_data:
                paging['previousUrl'] = get_cursor_url_from_graph_api_paging_url(request, paging_data['previous'])
    except Exception as e:
        print(e)
    return render_template('threads.jinja2', paging=paging, threads=threads, title='Threads')

@app.route('/threads/<thread_id>/replies')
@logged_in_user_checker
def thread_replies(thread_id):
    return show_replies(thread_id, True)

@app.route('/threads/<thread_id>/conversation')
@logged_in_user_checker
def thread_conversation(thread_id):
    return show_replies(thread_id, False)

@app.route('/manage_reply/<reply_id>', methods=['POST'])
@logged_in_user_checker
def manage_reply(reply_id):
    hide = request.args.get('hide')
    params = {}
    if hide:
        params[PARAMS__HIDE] = hide == 'true'
    url = build_graph_api_url(f"{reply_id}/manage_reply", {}, session[PARAMS__ACCESS_TOKEN])
    try:
        response = requests.post(url, params)
        return '', 200
    except Exception as e:
        return jsonify({'error': True, 'message': f"Error while hiding reply: {e}"}), 500

@app.route('/threads/<thread_id>/insights')
@logged_in_user_checker
def thread_insights(thread_id):
    since = request.args.get('since')
    until = request.args.get('until')
    params = {
        PARAMS__METRIC: ','.join([
            FIELD__VIEWS, FIELD__LIKES, FIELD__REPLIES, FIELD__REPOSTS, FIELD__QUOTES
        ])
    }
    if since:
        params['since'] = since
    if until:
        params['until'] = until

    url = build_graph_api_url(f"{thread_id}/insights", params, session[PARAMS__ACCESS_TOKEN])
    metrics = []
    try:
        response = requests.get(url)
        data = response.json()
        metrics = data.get('data', [])
    except Exception as e:
        print(e)

    for index in range(len(metrics)):
        get_insights_value(metrics, index)

    return render_template('thread_insights.jinja2', title='Thread Insights', threadId=thread_id, metrics=metrics, since=since, until=until)

@app.route('/logout')
def logout():
    session.clear()
    return render_template('index.jinja2', response='Logout successful!')

def show_replies(thread_id, is_top_level):
    username = request.args.get('username')
    before = request.args.get('before')
    after = request.args.get('after')
    limit = request.args.get('limit')
    params = {
        PARAMS__FIELDS: ','.join([
            FIELD__TEXT, FIELD__MEDIA_TYPE, FIELD__MEDIA_URL, FIELD__PERMALINK, FIELD__TIMESTAMP, FIELD__USERNAME, FIELD__HIDE_STATUS
        ]),
        'limit': limit or DEFAULT_THREADS_QUERY_LIMIT,
    }
    if before:
        params['before'] = before
    if after:
        params['after'] = after

    replies_or_conversation = 'replies' if is_top_level else 'conversation'
    url = build_graph_api_url(f"{thread_id}/{replies_or_conversation}", params, session[PARAMS__ACCESS_TOKEN])
    replies = []
    paging = {}
    try:
        response = requests.get(url)
        data = response.json()
        replies = data.get('data', [])
        if 'paging' in data:
            paging_data = data['paging']
            if 'next' in paging_data:
                paging['nextUrl'] = get_cursor_url_from_graph_api_paging_url(request, paging_data['next'])
            if 'previous' in paging_data:
                paging['previousUrl'] = get_cursor_url_from_graph_api_paging_url(request, paging_data['previous'])
    except Exception as e:
        print(e)

    template_name = 'thread_replies.jinja2' if is_top_level else 'thread_conversation.jinja2'
    return render_template(template_name, threadId=thread_id, username=username, paging=paging, replies=replies, manage=is_top_level, title='Replies')

if __name__ == '__main__':
    context = (os.path.join(os.path.dirname(__file__), '../threads-sample.meta.pem'),
               os.path.join(os.path.dirname(__file__), '../threads-sample.meta-key.pem'))
    app.run(host=HOST, port=PORT, ssl_context=context)
