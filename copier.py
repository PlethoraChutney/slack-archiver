import os
import sys
from flask import Flask, request, make_response, render_template
from slack import WebClient
from slack.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
from flask_socketio import SocketIO

app = Flask(__name__)
SocketIO(app, cors_allowed_origins='*')
client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
slack_events_adapter = SlackEventAdapter(os.environ['SLACK_SIGNING_SECRET'], "/slack/events", app)

def _event_handler(event_type, slack_event):

    if event_type == 'message':
        if 'bot_id' not in slack_event['event']:
            message_text = slack_event['event']['text'].lower()
            user_id = slack_event['event']['user']
            user_name = f'<@{user_id}>'
            channel = slack_event['event']['channel']
            if 'test' in message_text:
                response = client.chat_postMessage(
                    channel = channel,
                    text = 'Hi, got it'
                )

        return make_response('Read a message', 200, )


@app.route('/', methods = ['GET', 'POST'])
def process_request():
    slack_event = request.get_json()

    if 'challenge' in slack_event:
        return make_response(slack_event['challenge'], 200, {'content_type': 'application/json'})

    if 'event' in slack_event:
        event_type = slack_event['event']['type']

        return _event_handler(event_type, slack_event)
    else:
        return 'Hello world!'


if __name__ == "__main__":
    if sys.argv[1] == 'events':
        app.run(port=3000)
    elif sys.argv[1] == 'conversations':
        response = client.conversations_list(
            types = 'public_channel, private_channel'
        )
        for item in response['channels']:
            print(f"{item['name']}: {item['id']}")

# For my reference:
#   random: C8RTS98QM
#   general: C8SL1986A
#   about: CAH72QC3S
#   afscme_resources: CAJ24TXHB
#   bargaining_committee: GGAMDAFC1
#   cat: GGQ5FFQR0
