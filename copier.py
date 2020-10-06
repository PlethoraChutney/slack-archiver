import os
import sys
import json
from flask import Flask, request, make_response, render_template
from slack import WebClient
from slack.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
from flask_socketio import SocketIO

app = Flask(__name__)
client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])


if __name__ == "__main__":
    if sys.argv[1] == 'get_channels':
        response = client.conversations_list(
            types = 'public_channel, private_channel'
        )
        for item in response['channels']:
            print(f"{item['name']}: {item['id']}")

    elif sys.argv[1] == 'get_messages':
        input_channel = sys.argv[2]
        response = client.users_list()
        users = response["members"]

        user_dict = {}
        for user in users:
            user_dict[user['id']] = user['profile']['real_name_normalized']


        messages = []
        history = client.conversations_history(
            channel = input_channel
        )

        while history['has_more']:
            messages.extend(history['messages'])
            print(f'Fetching batch {history["response_metadata"]["next_cursor"]}')
            history = client.conversations_history(
                channel = input_channel,
                cursor = history["response_metadata"]["next_cursor"]
            )

        with open('bt_data.json', 'w') as outfile:
            json.dump(messages, outfile)

# For my reference:
#   random: C8RTS98QM
#   general: C8SL1986A
#   about: CAH72QC3S
#   afscme_resources: CAJ24TXHB
#   bargaining_committee: GGAMDAFC1
#   cat: GGQ5FFQR0
