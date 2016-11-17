# :dolphin: OP-Dolphin-Bot
This simple Python-based Slack Bot uses Slack's [Incoming WebHook](https://api.slack.com/incoming-webhooks) to automagically post OpenProject Activities.

In other words: It makes it easy to get notifications about the latest updates in OP.

It is not a plug**in** for OpenProject. Instead, it relies on the **external** OpenProject resources (currently the Atom feed only).

## Requirements:
- a 24/7 running web-server or PC (a Raspberry Pi would do the job, too!)
- Python 3.5/3.4 (tested) - may also work with >=3.0, but totally untested.
- OpenProject - tested with the Community Edition
- Slack with the [Incoming WebHook Integration](https://slack.com/apps/A0F7XDUAZ)

## Configuration:
1. Edit the variables in `starter.py`. You'll **need to configure** `SLACK_INCOMING_HOOK_URL`, `OP_BASE_URL`, `OP_PROJECT_ID` and `OP_RSS_KEY`
2. Start the python script (it needs to be *always running* if you do not want to get in an unsynchronized state)

## Features
**Q:** Why not use the Slack RSS integration since OpenProject has an Atom feed?

**A:** There would be **no** dolphin! :scream:

Just kidding. The real reasons:
- Configurable:
    - message format/look  is configurable by changing dictionary constants in `SlackMessageBuilder`
    - if you want extremely fresh updates every 5 seconds, simply change the `refresh_rate` constructor parameter in `DolphinBot`!
- Extensible:
    - maybe add OpenProject API support later? `util/op_projects_list.py` already contains an example on how to access the API
    - e.g. create more than one instance of the bot to watch multiple projects at one (by using threads)
- *Smart summary* feature: 
    - allows the bot to collect many updates
    - summarizes them in just one message to avoid "spamming" the slack channel
- More intelligent interpretation of the information
- Nicer look

## References:
- Test message look and feel: https://api.slack.com/docs/messages/builder
- Incoming WebHook: https://api.slack.com/incoming-webhooks
