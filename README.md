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
