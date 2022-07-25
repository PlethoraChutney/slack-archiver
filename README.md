# Slack Archiver
Pull messages and replies from all (or selected) channels.

![A video demonstrating use of the archive.](https://github.com/PlethoraChutney/slack-archiver/blob/main/readme_examples/archive-example.webm?raw=true)

## Purpose
Although the standard Slack plan allows you to download a JSON archive of
all public channels, sometimes it is desirable that private channels are archived
as well. This bot serves that purpose.

After installing and inviting union-archiver to the desired channels, use
the bot token to archive all messages into JSON.

## Requirements
In addition to the python packages (`python -m pip install -r requirements.txt`),
you must give your bot the following scopes:
  * `channels:history`
  * `channels:read`
  * `groups:history`
  * `groups:read`
  * `users:read`

The following scopes are optional, and only necessary if you want your bot to be
able to read DMs (`im:`) and group DMs (`mpim:`). The bot would need to be added
to these DMs, as well.
  * `im:history`
  * `im:read`
  * `mpim:history`
  * `mpim:read`

## Usage
Invite the bot to whatever channels you like (easiest way is to try to @ it in the channel)
and then run

`archiver.py scrape --token {your-slack-token} --archive-all`

or give it the
name of a specific channel(s):
  
`archiver.py scrape --token {slack-token} --select-channels general random`

If you've run the archiver before, be sure to give it your previous data
so that you don't lose the messages outside your current limit. By default
it will look for `slack_data.json` in the current directory, but you can
give it a different path if you like:

`archiver.py scrape --token {slack-token} --archive-all --input data/lab_slack.json --output new_data/lab_slack.json`

## To Do
 - Might be useful to download files as well

# Slack Visualizer
## Purpose
To keep everything simple, all your slack messages will be processed by the
Jinja templater to one HTML file per channel, along with an index file
to link to all the channels. That way search is implemented by browser, etc.

## Usage
Easy: `archiver.py visualize /path/to/slack_data.json workspace_name`

`workspace_name` is whatever you want to be in the HTML title tag and
the index heading, it's not that important but you do have to give it.

The HTML files are fairly simple, but they do display things in a nice
enough way. Along the left there is a sidebar with links to the other
channels. Each message will have the associated replies and emoji reactions,
and you can hover to show who reacted with what. Some links are messed
up because of the processing, but for the most part everything works.

## To Do
 - Eventually, it would probably be good to paginate the results

# Convert Old Data
If you used my slack archiver before I refactored it (haha...wow, thanks)
I have written a utility script to get the old "pile-of-JSONs" way of
doing things into the format this version expects.

## Usage
`convert_old.py --output /wherever/you/want/data.json {old_json_glob}`