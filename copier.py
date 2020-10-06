import os
import sys
import json
import time
from flask import Flask
from slack import WebClient
from slack.errors import SlackApiError

app = Flask(__name__)
# You need to put your slack bot token in the environment, and invite the
# bot to any channels you want to use this in
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

        out_users = sys.argv[3] + '_users.json'
        out_name = sys.argv[3] + '_messages.json'
        out_threads = sys.argv[3] + '_replies.json'

        with open(out_users, 'w') as outfile:
            json.dump(users, outfile)


        # This part is easy. Loop through the entire channel history until there
        # isn't any more, which Slack helpfully tells us
        messages = []
        history = client.conversations_history(
            channel = input_channel
        )

        while history['has_more']:
            messages.extend(history['messages'])
            print(f'Fetching message batch {history["response_metadata"]["next_cursor"]}')
            history = client.conversations_history(
                channel = input_channel,
                cursor = history["response_metadata"]["next_cursor"]
            )

        with open(out_name, 'w') as outfile:
            json.dump(messages, outfile)

        threads = {}

        for message in messages:
            ts = message['ts']
            print(f"Getting replies for: {ts}")
            replies = []
            try:
                thread = client.conversations_replies(
                    channel = input_channel,
                    ts = ts
                )

                replies.extend(thread['messages'])
            except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    delay = int(e.response.headers['Retry-After'])
                    print(f"Rate limited. Retrying in {delay} seconds")
                    time.sleep(delay)
                    continue
                else:
                    raise e


            while(thread['has_more']):
                try:
                    thread = client.conversations_replies(
                        channel = input_channel,
                        ts = ts,
                        cursor = thread["response_metadata"]["next_cursor"]
                    )
                    replies.extend(thread['messages'])
                except SlackApiError as e:
                    if e.response['error'] == 'ratelimited':
                        delay = int(e.response.headers['Retry-After'])
                        print(f"Rate limited. Retrying in {delay} seconds")
                        time.sleep(delay)
                        continue
                    else:
                        raise e
            threads[ts] = replies

        with open(out_threads, 'w') as outfile:
            json.dump(threads, outfile)

# For my reference:
#   random: C8RTS98QM
#   general: C8SL1986A
#   about: CAH72QC3S
#   afscme_resources: CAJ24TXHB
#   bargaining_committee: GGAMDAFC1
#   cat: GGQ5FFQR0
