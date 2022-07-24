#!/usr/bin/env python3
import os
import sys
import re
import json
import jinja2
import argparse
import logging
import time
from datetime import datetime
from slack import WebClient
from slack.errors import SlackApiError

script_dir = os.path.split(os.path.realpath(__file__))[0]

def create_client(token:str) -> WebClient:
    if token is None:
        try:
            token = os.environ['SLACK_TOKEN']
        except KeyError:
            log_wp.error('No slack bot token given.')
            sys.exit(1)

    client = WebClient(token = token)
    try:
        client.auth_test()
        log_wp.info('Slack authentication successful.')
    except SlackApiError as e:
        if e.response['error'] == 'invalid_auth':
            log_wp.error('Authentication failed. Check slack bot token.')
            sys.exit(2)
        else:
            raise e

    return client

# Scraping ----------------------------------------------------------------

class Scraper(object):
    def __init__(self, previous_data:dict, client:WebClient, targets:list) -> None:
        self.emoji_dict = {}
        with open(os.path.join(script_dir, 'emoji.json'), 'r') as f:
            emoji_list = json.load(f)
        for emoji in emoji_list:
            self.emoji_dict[emoji['short_name']] = ''.join(
                # get the emoji list into something a browser can read
                [f'&#x{e};' for e in emoji['unified'].split('-')]
            )

        self.message_data = previous_data
        self.client = client
        channels = client.conversations_list(
            types = 'public_channel, private_channel'
        )
        self.channel_dict = {c['name']: c['id'] for c in channels['channels']}
            
        if targets == 'all':
            self.targets = list(self.channel_dict.keys())
        else:
            good_targets = []
            for target in targets:
                if target in self.channel_dict.values():
                    log_wp.error('Give channel names, not IDs')
                    sys.exit(4)
                elif target in self.channel_dict:
                    good_targets.append(target)
                else:
                    log_wp.error(f'Channel "{target}" not found.')
                    sys.exit(4)
            self.targets = good_targets

        try:
            user_response = client.users_list()
        except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    delay = int(e.response.headers['Retry-After'])
                    log_wp.debug(f"Rate limited. Retrying in {delay} seconds")
                    time.sleep(delay)
                    user_response = client.users_list()

        self.users = {user['id']: user['profile']['real_name'] for user in user_response["members"]}

    def write_json(self, out_file:str) -> None:
        with open(out_file, 'w') as f:
            json.dump(self.message_data, f)

    def username_replace(self, text:str) -> str:
        log_wp.debug('Replacing usernames')
        for user_id, user_name in self.users.items():
            text = re.sub(f'<@{user_id}>', f'@{user_name}', text)

        log_wp.debug(f"New text: {text}")
        return text

    def url_replace(self, text:str) -> str:
        log_wp.debug('Replacing URLs')
        url_pattern = re.compile('<[^a](https?:\/\/.*\..*\..{3,})>')
        url_search = re.search(url_pattern, text)
        while url_search:
            log_wp.debug(f'Found url: {url_search.group(0)}')
            text = text.replace(
                url_search.group(0),
                f'<a href="{url_search.group(1)}">{url_search.group(1)}</a>'
            )
            url_search = re.search(url_pattern, text)

        log_wp.debug(f"New text: {text}")
        return text


    def emoji_replace(self, text:str) -> str:
        log_wp.debug('Replacing emoji')
        # first remove all URLs so we can trust that colons are
        # more-or-less only for emoji

        no_url_text = text[:]
        url_search = re.search('<a href.*<\/a>', no_url_text)
        while url_search:
            no_url_text = no_url_text.replace(url_search.group(0), '')
            url_search = re.search('<a href.*<\/a>', no_url_text)

        # now search the no-url text but replace in both
        e_pattern = re.compile(':(.*?):')
        e_match = re.search(e_pattern, no_url_text)
        while e_match:
            try:
                unicode_emoji = self.emoji_dict[e_match.group(1)]
                log_wp.debug(f'Replacing an emoji in {text}')
                log_wp.debug(f'No url text: {no_url_text}')
                text = text.replace(':' + e_match.group(1) + ':', unicode_emoji)
                no_url_text = no_url_text.replace(':' + e_match.group(1) + ':', unicode_emoji)
                log_wp.debug(f'Emoji replaced: {text}')
            except KeyError:
                log_wp.debug('Emoji replacement failed. Adding brackets.')
                text = text.replace(e_match.group(0), f"<{e_match.group(1)}>")
                no_url_text = no_url_text.replace(e_match.group(0), f"<{e_match.group(1)}>")

            e_match = re.search(e_pattern, no_url_text)

        return text


    def timestamps(self, channel:str) -> list:
        try:
            return self.message_data[channel].keys()
        except KeyError:
            return []

    def process_message_object(self, message:dict) -> dict:
        message['text'] = self.username_replace(message['text'])
        message['text'] = self.url_replace(message['text'])
        message['text'] = self.emoji_replace(message['text'])
        message['user'] = self.users[message['user']]
        message['format_ts'] = datetime.fromtimestamp(
            float(message['ts'])
        ).strftime('%Y-%m-%d %H:%M:%S')

        log_wp.debug('Perform emoji replacement')
        if 'reactions' in message:
            for reaction in message['reactions']:
                reaction['name'] = self.emoji_replace(f":{reaction['name']}:")
                reaction['users'] = [self.users[x] for x in reaction['users']]

        log_wp.debug('Done processing.')
        return message

    def process_messages(self, channel:str, messages:list) -> dict:
        processed_messages = {}
        log_wp.debug(f'Begin processing messages:')
        log_wp.debug('\n  '.join([m['text'] for m in messages]))
        for message in messages:
            log_wp.debug(f'Now on {message}')
            if message['ts'] in self.timestamps(channel):
                log_wp.debug(f'Message already in database.')
                continue

            log_wp.debug('Process message')
            message = self.process_message_object(message)

            message_dict = {
                'message': message
            }

            replies = []
            try:
                log_wp.debug(f"Getting replies to {message['text']}")
                reply_request = self.client.conversations_replies(
                    channel = self.channel_dict[channel],
                    ts = message['ts']
                )
            except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    delay = int(e.response.headers['Retry-After'])
                    log_wp.debug(f'Rate limited while fetching messages. Trying again in {delay} seconds.')
                    time.sleep(delay)
                    reply_request = self.client.conversations_replies(
                        channel = self.channel_dict[channel],
                        ts = message['ts']
                    )
                else:
                    raise e

            reply_batch = reply_request['messages']
            log_wp.debug(f'Got replies. Contains {len(reply_batch) - 1} replies')

            if len(reply_batch) != 1:
                
                # the first message in the replies is the original (parent)
                # message, so we need to delete it
                del reply_batch[0]
                log_wp.debug('Processing initial replies.')
                for reply in reply_batch:
                    reply = self.process_message_object(reply)
                    replies.append(reply)
                log_wp.debug('Done processing initial replies. Moving on.')

            while reply_request['has_more']:
                try:
                    log_wp.debug(f"Getting more replies to {message['text']}")
                    reply_request = self.client.conversations_replies(
                        channel = self.channel_dict[channel],
                        ts = message['ts'],
                        cursor = reply_request['reponse_metadata']['next_cursor']
                    )

                    log_wp.debug('Got more replies. Processing.')

                    for reply in reply_request['messages']:
                        reply = self.process_message_object(reply)
                        replies.append(reply)

                    log_wp.debug('Done processing. Checking for more replies')

                except SlackApiError as e:
                    if e.response['error'] == 'ratelimited':
                        delay = int(e.response.headers['Retry-After'])
                        log_wp.debug(f'Rate limited while fetching messages. Trying again in {delay} seconds.')
                        time.sleep(delay)
                        continue
                    else:
                        raise e

            log_wp.debug('No more replies. Adding to message dict')
            
            message_dict['replies'] = sorted(replies, key = lambda d: d['ts'])
            log_wp.debug('Sorted.')
            processed_messages[message['ts']] = message_dict
            log_wp.debug('Added to message dict.')

        log_wp.debug('All messages in this batch processed. Returning to parent task.')
        return processed_messages


    def scrape_channel(self, channel:str) -> None:
        # this function could likely improve. Rather than downloading
        # all the messages we have access to and checking if they're already
        # in the old data, we should start after the latest message for which
        # we have data. However, I ran into a bunch of API issues doing this
        # with the old script and gave up, since this is fast enough and also
        # speed doesn't really matter.

        log_wp.info(f'Scraping {channel}')
        message_batch = False
        while not message_batch:
            try:
                log_wp.debug('Getting new messages')
                message_batch = self.client.conversations_history(
                    channel = self.channel_dict[channel]
                )
            except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    delay = int(e.response.headers['Retry-After'])
                    log_wp.info(f'Rate limited while fetching messages. Trying again in {delay} seconds.')
                    time.sleep(delay)
                    continue
                elif e.response['error'] == 'not_in_channel':
                    log_wp.warning(f"Bot not in channel {channel}. Add it by tagging in the channel.")
                    self.message_data[channel] = {}
                    return
                else:
                    raise e

        if channel not in self.message_data:
            self.message_data[channel] = {}

        log_wp.debug('Processing message batch.')
        self.message_data[channel].update(
            self.process_messages(channel, message_batch['messages'])
        )

        while message_batch['has_more']:
            try:
                log_wp.debug('Getting more messages')
                message_batch = self.client.conversations_history(
                    channel = self.channel_dict[channel],
                    cursor = message_batch['response_metadata']['next_cursor']
                )
            except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    delay = int(e.response.headers['Retry-After'])
                    log_wp.info(f'Rate limited while fetching messages. Trying again in {delay} seconds.')
                    time.sleep(delay)
                    continue
                else:
                    raise e

            if channel not in self.message_data:
                self.message_data[channel] = {}

            log_wp.debug('Processing message batch')
            self.message_data[channel].update(
                self.process_messages(channel, message_batch['messages'])
            )


        log_wp.debug(f'Done with {channel}. Sorting and saving.')
        # sort by key
        self.message_data[channel] = dict(sorted(self.message_data[channel].items()))

    def scrape_targets(self):
        for channel in self.targets:
            self.scrape_channel(channel)
            

def scrape_session(args):
    try:
        with open(os.path.realpath(args.input), 'r') as f:
            previous_data = json.load(f)
    except FileNotFoundError:
        log_wp.warning("Input JSON not found. If this is the first time you're running the archiver that's fine.")
        previous_data = {}

    client = create_client(args.token)
    if args.archive_all:
        targets = 'all'
    else:
        targets = args.select_channels
    scraper = Scraper(previous_data, client, targets)
    scraper.scrape_targets()

    scraper.write_json(args.output)


# Visualization ---------------------------------------------------------------

templateLoader = jinja2.FileSystemLoader(searchpath = os.path.join(script_dir, 'templates'))
templateEnv = jinja2.Environment(loader = templateLoader)
template = templateEnv.get_template('index.html')

def visualize_data(args):
    try:
        with open(os.path.realpath(args.input), 'r') as f:
            slack_data = json.load(f)
    except FileNotFoundError:
        log_wp.error(f'Input JSON file "{os.path.realpath(args.input)}" does not exist.')
        sys.exit(5)

    # format for the JSON file is
    # { 'channel': 
    #   {'timestamp':
    #       {
    #           'message' {message},
    #           'replies': [
    #               {reply},
    #               {reply}
    #           ]
    #       }
    #   }
    # }

    for channel, channel_data in slack_data.items():
        output_text = template.render(
            channel = channel,
            messages = channel_data.values()
        )

        with open(f'{channel}.html', 'w', encoding='utf-8') as f:
            f.write(output_text)

# Argparse --------------------------------------------------------------------

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

# Scrape parser -------------------------------------------------------------

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
scrape.add_argument(
    '-i',
    '--input',
    help = 'Input JSON data file. Default is slack_data.json in current directory',
    default = 'slack_data.json'
)
scrape.add_argument(
    '-o',
    '--output',
    help = 'Output JSON file. Default is slack_data.json in current directory',
    default = 'slack_data.json'
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

# Visualization parser ---------------------------------------------------------

visualize = subparsers.add_parser(
    'visualize',
    help = 'Visualize Slack data JSON file'
)
visualize.set_defaults(func = visualize_data)
visualize.add_argument(
    'input',
    help = 'Input JSON data file.'
)
visualize.add_argument(
    '-o',
    '--output',
    help = 'Output directory for HTML files. Default is current directory.',
    default = os.getcwd()
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

    log_wp = logging.getLogger(__name__)
    logging_handler = logging.StreamHandler()
    logging_formatter = logging.Formatter('%(levelname)s: %(message)s')
    logging_handler.setFormatter(logging_formatter)
    log_wp.addHandler(logging_handler)
    log_wp.setLevel(level)

    args.func(args)