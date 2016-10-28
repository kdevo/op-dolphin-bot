# :dolphin: OP-Dolphin-Bot
This simple Python-based Slack Bot uses Slack's [Incoming WebHook](https://api.slack.com/incoming-webhooks) to automagically post OpenProject Activities.

In other words: It makes it easy to get notifications about the latest updates in OP.

It is **not** a plugin for Open Project. Instead, it relies on the external "interfaces" of OP (currently the Atom feed only).

## Requirements:
- a 24/7 running web-server or PC (a Raspberry Pi would do the job, too!)
- Python 3.5/3.4 - may also work with >=3.0, but totally untested.
- Open Project - tested with the Community version
- Slack with the [Incoming WebHook Integration](https://slack.com/apps/A0F7XDUAZ)

## Configuration:
1. Edit the variables in `starter.py`. You'll **need to configure** `SLACK_INCOMING_HOOK_URL`, `OP_BASE_URL`, `OP_PROJECT_ID` and `OP_RSS_KEY`
2. Start the python script (it needs to be *always running* if you do not want to get in an unsynchronized state)

## Features
**Q:** Why not use the Slack RSS integration since OpenProject has an Atom feed?

**A:** There would be **no** dolphin! :scream:

Just kidding. The real reasons:
- configurable:
    - message format/look  is configurable by changing dictionary constants in `SlackMessageBuilder`
    - if you want extremely fresh updates every 5 seconds, simply change the `check_sec` constructor parameter in `DolphinBot`!
- extensibility:
    - maybe add OpenProject API support later? `util/op_projects_list.py` already contains an example on how to access the API
    - e.g. create more than one instance of the bot to watch multiple projects at one (by using threads)
- information is interpreted more intelligent
- *smart summary* feature allows the bot to collect updates and summarize them
- nicer look

## References:
- Test message look and feel: https://api.slack.com/docs/messages/builder
- Incoming WebHook: https://api.slack.com/incoming-webhooks
