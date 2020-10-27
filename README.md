# Slack Archiver
Pull messages and replies from all (or selected) channels.

## Purpose
Although the standard Slack plan allows you to download a JSON archive of
all public channels, sometimes it is desirable that private channels are archived
as well. This bot serves that purpose.

After installing and inviting union-archiver to the desired channels, use
the bot token to archive all messages into JSON.

## Requirements
In addition to the python packages, you must give your bot the following scopes:
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

# Slack Visualizer
An extremely rudamentary visualizer for the JSON archives. Uses a Jinja2 template
to make a huge, plain html file for each channel archive. Just need to point it
to the directory which contains all of your channels' .json files, it'll do the
rest. Right now it doesn't include reactions, and links are not present for some
reason.
