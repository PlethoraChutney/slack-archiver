import os
import glob
import sys
import re
import json
import argparse
import logging
import time
from datetime import datetime
from archiver import Scraper, archive_logger

script_dir = os.path.split(os.path.realpath(__file__))[0]

def main(args):
    json_files = [os.path.realpath(x) for x in glob.glob(args.input) if os.path.exists(x) and x.endswith('.json') and ('replies' in x or 'users' in x)]
    
    converter = Scraper({}, None, [], no_connection = True)

    base_dir = os.path.split(json_files[0])[0]
    channels = list(set('_'.join(os.path.split(x)[1].split('_')[:-1]) for x in json_files))

    for channel in channels:
        message_data = {}
        archive_logger.debug(f'Loading replies for {channel}')

        try:
            with open(os.path.join(base_dir, channel + '_users.json'), 'r') as f:
                converter.users = {user['id']: user['profile']['real_name'] for user in json.load(f)}
        except FileNotFoundError:
            archive_logger.warning(f"Couldn't find users for {channel}. Skipping.")
            continue

        try:
            with open(os.path.join(base_dir, channel + '_replies.json'), 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            archive_logger.warning(f"Couldn't find messages for {channel}. Skipping.")
            continue

        for ts, messages in data.items():
            for i in range(len(messages)):
                messages[i] = converter.process_message_object(messages[i])

            message_data[ts] = {
                'message': messages[0],
                'replies': messages[1:] if len(messages) > 1 else []
            }
        
        converter.message_data[channel] = message_data

    converter.write_json(args.output)
        

parser = argparse.ArgumentParser(
    description='Convert old loose JSON files into modern single-file format.'
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

parser.add_argument(
    'input',
    help = 'Loose JSON files. Glob format.'
)
parser.add_argument(
    '--output',
    help = 'Output JSON file. Default "slack_data.json" in current dir',
    default = 'slack_data.json'
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

    main(args)