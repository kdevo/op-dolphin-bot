# :dolphin: OP-Dolphin-Bot
This Slack-Bot uses the "Incoming Webhook" to automagically post OpenProject Activities.

## Requirements:
- an always-on PC/web-server
- Python 3.5 - may also work with >=3.0, totally untested
- Slack with [Incoming Webhook Integration](https://my.slack.com/services/new/incoming-webhook/)
- OpenProject (of course)

## Configuration:
1. Edit the CONFIGURATION variables in the `op-dolphin-bot.py`, you'll need two URLs:
  - the Atom feed URL in the "Activities" tab of OpenProject
  - your personal Slack Webhook URL
2. Start the python script (it needs to be *always running* if you do not want to get in an unsychronized state)

## Why not use the RSS integration since OpenProject has an Atom feed?
There would be **no** dolphin! Just kidding. The real reasons:
- this bot should be always faster, reading every 5 seconds per default
- extensibility, maybe add OpenProject API support later?
- information is interpreted a bit more intelligent
- nicer look

## References:
- Test message look and feel: https://api.slack.com/docs/messages/builder
- Incoming Webhook: https://api.slack.com/incoming-webhooks
