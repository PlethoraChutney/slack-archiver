# Slack Archiver
Pull messages and replies from all (or selected) channels.

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

`archiver.py --token {your-slack-token} --archive-all`

or give it the
name of a specific channel:
  
`archiver.py --token {slack-token} --archive-channel general`

# Slack Visualizer
## Purpose
An extremely rudimentary visualizer for the JSON archives. Uses a Jinja2 template
to make a huge, plain html file for each channel archive. Just need to point it
to the directory which contains all of your channels' .json files, it'll do the
rest.

## Usage
Easy: `visualizer.py /path/to/json/directory`

## To Do
 - Visualizer doesn't pull links right now
 - Might be useful to download files as well
 - Eventually, it would probably be good to paginate the results

Also, this is one of those projects that kinda grew organically out of a much
simpler script. Should probably just re-build it now that it's this.