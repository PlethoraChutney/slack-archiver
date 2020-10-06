import os
import sys
import json
import time
import argparse
from slack import WebClient
from slack.errors import SlackApiError

def get_channels(client):
    response = client.conversations_list(
        types = 'public_channel, private_channel'
    )

    channel_dict = {}
    for c in response['channels']:
        channel_dict[c['name']] = c['id']

    return(channel_dict)


def get_messages(client, channel, name):

    out_users = name + '_users.json'
    out_name = name + '_messages.json'
    out_threads = name + '_replies.json'

    response = client.users_list()
    users = response["members"]

    with open(out_users, 'w') as outfile:
        json.dump(users, outfile)


    # This part is easy. Loop through the entire channel history until there
    # isn't any more, which Slack helpfully tells us
    messages = []
    history = client.conversations_history(
        channel = channel
    )

    while history['has_more']:
        try:
            messages.extend(history['messages'])
            print(f'Fetching {name} message batch {history["response_metadata"]["next_cursor"]}')
            history = client.conversations_history(
                channel = channel,
                cursor = history["response_metadata"]["next_cursor"]
            )
        except SlackApiError as e:
            if e.response['error'] == 'ratelimited':
                delay = int(e.response.headers['Retry-After'])
                print(f"Rate limited. Retrying in {delay} seconds")
                time.sleep(delay)
                continue
            else:
                raise e

    with open(out_name, 'w') as outfile:
        json.dump(messages, outfile)

    get_replies(client, channel, name, messages)

def get_replies(client, channel, name, messages):
    threads = {}

    # Loop through all messages to check for replies. If we find them, follow
    # a similar procedure as above.
    for message in messages:
        ts = message['ts']
        print(f"Getting replies in {name} for: {ts}")
        replies = []
        try:
            thread = client.conversations_replies(
                channel = channel,
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
                    channel = channel,
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


parser = argparse.ArgumentParser(description = 'Archive messages from Slack')
parser.add_argument('--token',
                    help = 'Slack bot authentication token. If this option is not used, will pull token from SLACK_BOT_TOKEN environment variable.',
                    default = os.environ['SLACK_BOT_TOKEN'])
parser.add_argument('--get-channels',
                    help = 'Print list of channels and ids',
                    action = 'store_true')
parser.add_argument('--archive-channel',
                    help = 'Archive a specific channel(s) by name',
                    type = str,
                    nargs = '+')
parser.add_argument('--archive-all',
                    help = 'Archive all channels of which the bot is a member',
                    action = 'store_true')

def main():
    args = parser.parse_args()
    client = WebClient(token = args.token)

    try:
        client.auth_test()
        print('Authentication successful.')
    except SlackApiError as e:
        if e.response['error'] == 'invalid_auth':
            print('Authentication failed. Check slack bot token.')
        else:
            raise e

    channel_dict = get_channels(client)
    if args.get_channels:
        for key in channel_dict.keys():
            print(f"{key} {channel_dict[key]}")

    if args.archive_channel:
        channel_list = args.archive_channel
    elif args.archive_all:
        channel_list = channel_dict.keys()

    if channel_list:
        for channel in channel_list:
            try:
                get_messages(client, channel_dict[channel], channel)
            except KeyError:
                print(f'No channel called {channel}. Available channels:')
                print(', '.join([key for key in channel_dict.keys()]))
            except SlackApiError as e:
                if e.response['error'] == 'not_in_channel':
                    print(f'WARNING: Bot is not in {channel}. Skipping.')
                else:
                    raise e




if __name__ == "__main__":
    main()
