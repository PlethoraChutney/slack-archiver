import json
import os
import jinja2
from datetime import datetime

with open(os.path.join('data', 'bargaining-committee_messages.json'), 'r') as infile:
    messages = json.load(infile)
with open(os.path.join('data', 'bargaining-committee_users.json'), 'r') as infile:
    raw_users = json.load(infile)
with open(os.path.join('data', 'bargaining-committee_replies.json'), 'r') as infile:
    replies = json.load(infile)

users = {}
for user in raw_users:
    users[user['id']] = user['profile']['real_name']

for timestamp in replies.keys():
    for message in replies[timestamp]:
        for key in users:
            message['text'] = message['text'].replace(key, users[key])
        message['format_ts'] = datetime.fromtimestamp(float(message['ts'])).strftime('%Y-%m-%d %H:%M:%S')


templateLoader = jinja2.FileSystemLoader(searchpath = "templates")
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "index.html"
template = templateEnv.get_template(TEMPLATE_FILE)

output_text = template.render(messages = replies.values(), users = users)

with open('gru-archive.html', 'w', encoding = 'utf-8') as outfile:
    outfile.write(output_text)
