#!/usr/bin/env python3
import os
import sys
import re
import json
import argparse
import logging
import time
import datetime
from slack import WebClient
from slack.errors import SlackApiError

script_dir = os.path.split(os.path.realpath(__file__))[0]

def create_client(token:str) -> WebClient:
    if token is None:
        try:
            token = os.environ['SLACK_TOKEN']
        except KeyError:
            logging.error('No slack bot token given.')
            sys.exit(1)

    client = WebClient(token = token)
    try:
        client.auth_test()
        logging.info('Slack authentication successful.')
    except SlackApiError as e:
        if e.response['error'] == 'invalid_auth':
            logging.error('Authentication failed. Check slack bot token.')
            sys.exit(2)
        else:
            raise e

    return client

class Scraper(object):
    def __init__(self, client:WebClient, targets:list) -> None:
        self.emoji_dict = {}
        with open(os.path.join(script_dir, 'emoji.json'), 'r') as f:
            emoji_list = json.load(f)
        for emoji in emoji_list:
            self.emoji_dict[emoji['short_name']] = ''.join(
                # get the emoji list into something a browser can read
                [f'&#x{e};' for e in emoji['unified'].split('-')]
            )


        self.client = client
        channels = client.conversations_list(
            types = 'public_channel, private_channel'
        )
        self.channel_dict = {c['name']: c['id'] for c in channels['channels']}
        self.message_data = {}
            
        if targets == 'all':
            self.targets = list(self.channel_dict.keys())
        else:
            good_targets = []
            for target in targets:
                if target in self.channel_dict.values():
                    logging.error('Give channel names, not IDs')
                    sys.exit(4)
                elif target in self.channel_dict:
                    good_targets.append(target)
                else:
                    logging.error(f'Channel "{target}" not found.')
                    sys.exit(4)
            self.targets = good_targets

        try:
            user_response = client.users_list()
        except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    delay = int(e.response.headers['Retry-After'])
                    logging.debug(f"Rate limited. Retrying in {delay} seconds")
                    time.sleep(delay)
                    user_response = client.users_list()

        self.users = {user['id']: user['profile']['real_name'] for user in user_response["members"]}

    def username_replace(self, text:str) -> str:
        for user_id, user_name in self.users.items():
            text = re.sub(f'<@{user_id}>', f'@{user_name}', text)

        return text

    def emoji_replace(self, text:str) -> str:
        e_match = re.search(':(.*?):', text)
        while e_match:
            try:
                unicode_emoji = self.emoji_dict[e_match.group(1)]
                text = text.replace(e_match.group(0), unicode_emoji)
            except KeyError:
                text = text.replace(e_match.group(0), f"<{e_match.group(1)}>")

            e_match = re.search(':(.*?):', text)

        return text


    def timestamps(self, channel) -> list:
        try:
            return self.message_data[channel].keys()
        except KeyError:
            return []

    def process_messages(self, channel:str, messages:list) -> dict:
        processed_messages = {}
        for message in messages:
            if float(message['ts']) in self.timestamps(channel):
                continue

            message['text'] = self.username_replace(message['text'])
            message['text'] = self.emoji_replace(message['text'])

            message_dict = {
                'message': message
            }

            replies = []
            try:
                reply_request = self.client.conversations_replies(
                    channel = self.channel_dict[channel],
                    ts = message['ts']
                )
            except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    delay = int(e.response.headers['Retry-After'])
                    logging.info(f'Rate limited while fetching messages. Trying again in {delay} seconds.')
                    time.sleep(delay)
                    reply_request = self.client.conversations_replies(
                        channel = self.channel_dict[channel],
                        ts = message['ts']
                    )
                else:
                    raise e

            reply_batch = reply_request['messages']

            if len(reply_batch) != 1:
                
                # the first message in the replies is the original (parent)
                # message, so we need to delete it
                del reply_batch[0]
                for reply in reply_batch:
                    reply['text'] = self.username_replace(reply['text'])
                    reply['text'] = self.emoji_replace(reply['text'])
                    reply['ts'] = float(reply['ts'])
                    replies.append(reply)

            while reply_request['has_more']:
                try:
                    reply_request = self.client.conversations_replies(
                        channel = self.channel_dict[channel],
                        ts = message['ts'],
                        cursor = reply_request['reponse_metadata']['next_cursor']
                    )

                    for reply in reply_request['messages']:
                        reply['text'] = self.username_replace(reply['text'])
                        reply['text'] = self.emoji_replace(reply['text'])
                        reply['ts'] = float(reply['ts'])
                        replies.append(reply)

                except SlackApiError as e:
                    if e.response['error'] == 'ratelimited':
                        delay = int(e.response.headers['Retry-After'])
                        logging.info(f'Rate limited while fetching messages. Trying again in {delay} seconds.')
                        time.sleep(delay)
                        continue
                    else:
                        raise e
            
            message_dict['replies'] = sorted(replies, key = lambda d: d['ts'])
            processed_messages[float(message['ts'])] = message_dict

        return processed_messages


    def scrape_channel(self, channel):
        message_batch = False
        while not message_batch:
            try:
                message_batch = self.client.conversations_history(
                    channel = self.channel_dict[channel]
                )
            except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    delay = int(e.response.headers['Retry-After'])
                    logging.info(f'Rate limited while fetching messages. Trying again in {delay} seconds.')
                    time.sleep(delay)
                    continue
                else:
                    raise e

        if channel not in self.message_data:
            self.message_data[channel] = {}

        self.message_data[channel].update(
            self.process_messages(channel, message_batch['messages'])
        )

        while message_batch['has_more']:
            try:
                message_batch = self.client.conversations_history(
                    channel = self.channel_dict[channel],
                    cursor = message_batch['response_metadata']['next_cursor']
                )
            except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    delay = int(e.response.headers['Retry-After'])
                    logging.info(f'Rate limited while fetching messages. Trying again in {delay} seconds.')
                    time.sleep(delay)
                    continue
                else:
                    raise e

            if channel not in self.message_data:
                self.message_data[channel] = {}

            self.message_data[channel].update(
                self.process_messages(channel, message_batch['messages'])
            )

        # sort by key
        self.message_data[channel] = dict(sorted(self.message_data[channel].items()))

    def scrape_channels(self):
        for channel in self.targets:
            self.scrape_channel(channel)
            




def scrape_session(args):
    client = create_client(args.token)
    if args.archive_all:
        targets = 'all'
    else:
        targets = args.select_channels
    scraper = Scraper(client, targets)
    scraper.scrape_channels()


    for channel in scraper.targets:
        for message in scraper.message_data[channel].values():
            print(message['message']['text'])
    

parser = argparse.ArgumentParser(
    description= 'Scrape a slack workspace and save the messages to JSON'
)

verbosity = parser.add_argument_group('verbosity')
vxg = verbosity.add_mutually_exclusive_group()
vxg.add_argument(
    '-q', '--quiet',
    help = 'Print Errors only',
    action = 'store_const',
    dest = 'verbosity',
    const = 'q'
)
vxg.add_argument(
    '-v', '--verbose',
    help = 'Print Info, Warnings, and Errors. Default state.',
    action = 'store_const',
    dest = 'verbosity',
    const = 'v'
)
vxg.add_argument(
    '--debug',
    help = 'Print debug output.',
    action = 'store_const',
    dest = 'verbosity',
    const = 'd'
)

subparsers = parser.add_subparsers()

scrape = subparsers.add_parser(
    'scrape',
    help = 'Scrape the Slack workspace'
)
scrape.set_defaults(func = scrape_session)
scrape.add_argument(
    '-t',
    '--token',
    help = 'Slack bot token. Should start with "xoxb". If not provided, will be pulled from $SLACK_TOKEN'
)
channels = scrape.add_mutually_exclusive_group(required = True)
channels.add_argument(
    '--archive-all',
    action = 'store_true',
    help = 'Archive all channels for which the bot is a member'
)
channels.add_argument(
    '--select-channels',
    nargs = '+',
    help = 'Space-separated list of channel names'
)

if __name__ == '__main__':
    args = parser.parse_args()

    levels = {
        'q': logging.ERROR,
        'v': logging.INFO,
        'd': logging.DEBUG
    }

    try:
        level = levels[args.verbosity]
    except KeyError:
        level = logging.INFO

    logging.basicConfig(
        level = level,
        format = '{levelname}: {message} ({filename})',
        style = '{'
    )

    args.func(args)