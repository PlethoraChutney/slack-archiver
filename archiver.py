#!/usr/bin/env python3
import os
import sys
import json
import time
import argparse
import logging
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
    logging.info('Fetching %s messages', name)
    out_users = name + '_users.json'
    out_name = name + '_messages.json'

    response = client.users_list()
    users = response["members"]

    with open(out_users, 'w') as outfile:
        json.dump(users, outfile)

    # Loop through the entire channel history until there
    # isn't any more, which Slack helpfully tells us
    messages = []
    history = client.conversations_history(
        channel = channel
    )

    while history['has_more']:
        try:
            messages.extend(history['messages'])
            logging.debug('Fetching %s message batch %s', name, history["response_metadata"]["next_cursor"])
            history = client.conversations_history(
                channel = channel,
                cursor = history["response_metadata"]["next_cursor"]
            )
        except SlackApiError as e:
            if e.response['error'] == 'ratelimited':
                delay = int(e.response.headers['Retry-After'])
                logging.debug("Rate limited. Retrying in %i seconds", delay)
                time.sleep(delay)
                continue
            else:
                raise e

    with open(out_name, 'w') as outfile:
        json.dump(messages, outfile)

    get_replies(client, channel, name, messages)


def get_replies(client, channel, name, messages):
    out_threads = name + '_replies.json'
    threads = {}

    # Loop through all messages to check for replies. If we find them, follow
    # a similar procedure as above.
    #
    # Use the message iterator instead of a for loop otherwise we don't retry
    # replies for messages which get rate limited.
    message_iterator = 0
    while message_iterator < len(messages):
        ts = messages[message_iterator]['ts']
        logging.debug("Getting replies in %s for: %s", name, ts)
        replies = []
        try:
            thread = client.conversations_replies(
                channel = channel,
                ts = ts
            )

            replies.extend(thread['messages'])
            while(thread['has_more']):
                logging.debug('%s has more replies', ts)
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
                        logging.debug("Rate limited. Retrying in %i seconds", delay)
                        time.sleep(delay)
                        continue
                    else:
                        raise e
            message_iterator += 1
        except SlackApiError as e:
            if e.response['error'] == 'ratelimited':
                delay = int(e.response.headers['Retry-After'])
                logging.debug("Rate limited. Retrying in %i seconds", delay)
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
                    default = None)
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
parser.add_argument('-v', '--verbose',
                    help = 'Increase logger verbosity',
                    action = 'count',
                    default = 0)


def main():
    args = parser.parse_args()

    if args.token is None:
        try:
            token = os.environ['SLACK_BOT_TOKEN']
        except KeyError as e:
            logging.error('Must give slack bot token as environment variable or argument')
            sys.exit(1)
    else:
        token = args.token

    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(len(levels) - 1, args.verbose)]
    logging.basicConfig(level = level)


    try:
        client = WebClient(token = args.token)
    except KeyError as e:
        logging.error('Failed to create Slack Client. Check bot token.')
        sys.exit(1)

    try:
        client.auth_test()
        logging.info('Authentication successful.')
    except SlackApiError as e:
        if e.response['error'] == 'invalid_auth':
            logging.error('Authentication failed. Check slack bot token.')
            sys.exit(1)
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
    else:
        channel_list = False

    if channel_list:
        for channel in channel_list:
            try:
                get_messages(client, channel_dict[channel], channel)
            except KeyError:
                logging.error("No channel called %s. Available channels:\n %s", channel, ', '.join([key for key in channel_dict.keys()]))
            except SlackApiError as e:
                if e.response['error'] == 'not_in_channel':
                    logging.warning('WARNING: Bot is not in %s. Skipping.', channel)
                else:
                    raise e


if __name__ == "__main__":
    main()
    logging.info('Done.')
