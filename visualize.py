import json
import os
import jinja2

with open(os.path.join('data', 'cat_messages.json'), 'r') as infile:
    messages = json.load(infile)
with open(os.path.join('data', 'cat_users.json'), 'r') as infile:
    raw_users = json.load(infile)

users = {}
for user in raw_users:
    users[user['id']] = user['profile']['real_name']

for message in messages:
    for key in users:
        message['text'] = message['text'].replace(key, users[key])


templateLoader = jinja2.FileSystemLoader(searchpath = "templates")
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "index.html"
template = templateEnv.get_template(TEMPLATE_FILE)
output_text = template.render(messages = messages, users = users)

with open('gru-archive.html', 'w', encoding = 'utf-8') as outfile:
    outfile.write(output_text)
