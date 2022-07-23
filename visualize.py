import json
import os
import jinja2
import argparse
import re
from datetime import datetime

scriptdir = os.path.split(os.path.realpath(__file__))[0]
templateLoader = jinja2.FileSystemLoader(searchpath = os.path.join(scriptdir, 'templates'))
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "index.html"
template = templateEnv.get_template(TEMPLATE_FILE)

emoji_search = re.compile(':(.*?):')

emoji_dict = {}
with open(os.path.join(scriptdir, 'emoji.json'), 'r') as f:
    emoji_list = json.load(f)
for emoji in emoji_list:
    emoji_dict[emoji['short_name']] = ''.join(
        # get the emoji list into something a browser can read
        [f'&#x{x};' for x in emoji['unified'].split('-')])



def visualize(path, channel_name):
    user_file = f"{channel_name}_users.json"
    reply_file = f"{channel_name}_replies.json"

    with open(os.path.join(path, user_file), 'r') as infile:
        raw_users = json.load(infile)
    try:
        with open(os.path.join(path, reply_file), 'r') as infile:
            replies = json.load(infile)
    except FileNotFoundError:
        return

    users = {}
    for user in raw_users:
        users[user['id']] = user['profile']['real_name']

    replies = dict(sorted(replies.items(), reverse = True))

    for timestamp in replies.keys():
        for message in replies[timestamp]:
            for key in users:
                message['text'] = message['text'].replace(key, users[key])
            message['format_ts'] = datetime.fromtimestamp(
                float(message['ts'])
                ).strftime('%Y-%m-%d %H:%M:%S')

            e_match = re.search(emoji_search, message['text'])
            while e_match:
                try:
                    unicode_emoji = emoji_dict[e_match.group(1)]
                    message['text'] = re.sub(emoji_search, unicode_emoji, message['text'])
                except KeyError:
                    # not really worth figuring out a way to handle stuff that's not in the
                    # emoji dict
                    break
                e_match = re.search(emoji_search, message['text'])

            
            
            if 'reactions' in message:
                for emoji_type in message['reactions']:
                    try:
                        unicode_emoji = emoji_dict[emoji_type['name']]
                    except KeyError:
                        if emoji_type['name'] in [
                            'column',
                            'enac',
                            'troll',
                            'thumbsup_all',
                            'vitrobot',
                            'hotspur'
                        ]:
                            continue
                        split_emoji = emoji_type['name'].split('::')
                        unicode_emoji = []
                        for emoji in split_emoji:
                            unicode_emoji.append(emoji_dict[emoji])
                        unicode_emoji = ''.join(unicode_emoji)
                    count = emoji_type['count']
                    try:
                        message['processed_reactions'].append([unicode_emoji, count])
                    except KeyError:
                        message['processed_reactions'] = [[unicode_emoji, count]]

    output_text = template.render(
        channel = channel_name,
        messages = replies.values(),
        users = users)

    outfile_name = f"{channel_name}.html"
    with open(outfile_name, 'w', encoding = 'utf-8') as outfile:
        outfile.write(output_text)


def main():
    args = parser.parse_args()
    files = os.listdir(args.data_dir)

    channels = []
    for file in files:
        channel = '_'.join(file.split('_')[:-1])
        if channel and channel not in channels:
            channels.append(channel)

    for channel in channels:
        visualize(args.data_dir, channel)


parser = argparse.ArgumentParser(description = 'Create html files from slack JSON')
parser.add_argument('data_dir', help = 'Where JSON files are')

if __name__ == '__main__':
    main()
