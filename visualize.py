import json
import os
import jinja2
import argparse
from datetime import datetime

templateLoader = jinja2.FileSystemLoader(searchpath = "templates")
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "index.html"
template = templateEnv.get_template(TEMPLATE_FILE)


def visualize(path, channel_name):
    user_file = f"{channel_name}_users.json"
    reply_file = f"{channel_name}_replies.json"

    with open(os.path.join(path, user_file), 'r') as infile:
        raw_users = json.load(infile)
    with open(os.path.join(path, reply_file), 'r') as infile:
        replies = json.load(infile)

    users = {}
    for user in raw_users:
        users[user['id']] = user['profile']['real_name']

    for timestamp in replies.keys():
        for message in replies[timestamp]:
            for key in users:
                message['text'] = message['text'].replace(key, users[key])
            message['format_ts'] = datetime.fromtimestamp(float(message['ts'])).strftime('%Y-%m-%d %H:%M:%S')

    output_text = template.render(messages = replies.values(), users = users)

    outfile_name = f"{channel_name}-archive.html"
    with open(outfile_name, 'w', encoding = 'utf-8') as outfile:
        outfile.write(output_text)


def main():
    args = parser.parse_args()
    files = os.listdir(args.data_dir)

    channels = []
    for file in files:
        channel = '_'.join(file.split('_')[:-1])
        if channel not in channels:
            channels.append(channel)

    for channel in channels:
        visualize(args.data_dir, channel)


parser = argparse.ArgumentParser(description = 'Create html files from slack JSON')
parser.add_argument('data_dir', help = 'Where JSON files are')

if __name__ == '__main__':
    main()
