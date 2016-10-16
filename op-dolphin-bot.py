""" OP-Dolphin-Bot: OpenProject Activities -> Slack (by kdevo)
This is a Slack Bot that watches for Open Project activities and posts them automagically.

Requirements:
- Python 3.5 (may also work with >=3.0, totally untested)
- an always-on running PC/web-server

Configuration:
- Edit the variables in START CONFIGURATION below

References:
- Test message look and feel: https://api.slack.com/docs/messages/builder
- Incoming Webhook: https://api.slack.com/incoming-webhooks
"""

from string import Template
import logging
import json
import urllib.request
# import requests -> maybe use this later for API access and basic auth
import time
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ElemTree

# START CONFIGURATION
SLACK_INCOMING_HOOK_URL = ""
OPENPROJECT_ACTIVITY_ATOM_URL = "https:/YOUR-OPENPROJECT-ACTIVITY-ATOM.URL" # &show_documents=1&show_meetings=1&show_messages=1&show_news=1&show_wiki_edits=1&show_work_packages=1
# END CONFIGURATION

PROGRAM_NAME = "op-dolphin-bot"
PROGRAM_VERSION = "v0.2"

logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', level=logging.DEBUG)
logging.info("Started %s. Current version: %s", PROGRAM_NAME, PROGRAM_VERSION)


class OpenProjectActivities:
    """ Basically a tiny feed reader - is used to read the OpenProject activities (atom feed)"""

    _PREFIX = {'feed': 'http://www.w3.org/2005/Atom'}
    _TAGS = {'feed:title': 'title',
             'feed:id': 'url',
             'feed:updated': 'datetime',
             'feed:author/feed:name': 'author'}

    def __init__(self, atom_url):
        self._atom_url = atom_url

        self._update_time = None
        self._last_deliver_time = None
        self._xml_entries = None
        self._refresh_xml_entries()
        self._last_deliver_time = self._update_time

    def deliver_updates(self):
        self._refresh_xml_entries()
        result = []
        if self._last_deliver_time < self._update_time:
            logging.info("Change detected, update time: %s", self._update_time)
            for entry in self._xml_entries:
                if self._last_deliver_time < self._convert_time(entry):
                    result.append(self._build_entry(entry))
            self._last_deliver_time = self._update_time
        return result

    def _refresh_xml_entries(self):
        with urllib.request.urlopen(self._atom_url) as atom_file:
            root = ElemTree.fromstring(atom_file.read().decode('utf8'))
        self._update_time = self._convert_time(root)
        if self._last_deliver_time is not None and self._update_time > self._last_deliver_time:
            self._xml_entries = root.findall('feed:entry', self._PREFIX)

    @staticmethod
    def _guess_type(url):
        for check in ('news', 'work_packages', 'documents', 'meetings', 'wiki'):
            if '/{0}'.format(check) in url:
                return check.replace('_', ' ').capitalize()

    def _build_entry(self, xml_entry):
        entry = {}
        for kv in self._TAGS.items():
            entry[kv[1]] = xml_entry.find(kv[0], self._PREFIX).text
        entry['type'] = OpenProjectActivities._guess_type(entry['url'])
        entry['datetime'] = self._convert_time(xml_entry)
        return entry

    def _convert_time(self, xml_entry, to_local_tz=True):
        # Assuming Zulu UTC (+0) military time zone in Atom feed, that's what the 'Z' stands for at the end:
        dt = datetime.strptime(xml_entry.find('feed:updated', self._PREFIX).text, "%Y-%m-%dT%H:%M:%SZ")
        if to_local_tz:
            return dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
        else:
            return dt


class SlackConnection:
    """ Used to connect to slack and post (formatted) messages """

    # Base message ($vars need to be substituted by using build_json method)
    _MESSAGE = \
        {
            'username': PROGRAM_NAME,
            'icon_emoji': ":dolphin:",
            'attachments': [{
                'title': "OpenProject Update",
                'title_link': "$url",
                'color':  "#$color",  # "00b7c3" is dolphin-blue (if type-dependent colouring is not needed)
                'text':  "$text",
                'fields': [
                    {
                        'title': "Type",
                        'value': "$type_emoji $type",
                        'short': True
                    },
                    {
                        'title': "Author",
                        'value': "$author",
                        'short': True
                    }
                ],
                'ts': '$timestamp',
                'footer': "{0} {1}".format(PROGRAM_NAME, PROGRAM_VERSION),
                'mrkdwn_in': ["text"]
            }]
        }

    # Maps the types to a tuple with emoji [0] and color [1] (html-based)
    _TYPE_MAP = {
        None: (':coffee:', '00b7c3'),
        'Work packages': (':package:', '00b7c3'),
        'News': (':newspaper:', '248c15'),
        'Wiki': (':book:', '11696d'),
        'Documents': (':page_facing_up:', '116d37'),
        'Meetings': (':calendar:', 'e0283a')
    }
    _TO_HIGHLIGHT = ('In progress', 'New', 'Closed')

    def __init__(self, url_hook, highlight_keywords=True):
        self.url_hook = url_hook
        self.highlight_keywords = highlight_keywords

    def post(self, json_message):
        logging.debug('Connecting to "%s" for POST request.', self.url_hook)
        request = urllib.request.Request(self.url_hook, headers={'Content-type': "application/json"})
        with urllib.request.urlopen(request, bytes(json_message, 'utf8')) as resp:
            resp = resp.read().decode('utf8')
            logging.debug("Response: %s.", resp.upper())

    def build_json(self, entry):
        title = entry['title']
        if self.highlight_keywords:
            for kw in self._TO_HIGHLIGHT:
                if kw in entry['title']:
                    title = title.replace(kw, '_{0}_'.format(kw))
        return Template(json.dumps(self._MESSAGE)).safe_substitute(type=entry['type'],
                                                                   color=self._TYPE_MAP[entry['type']][1],
                                                                   type_emoji=self._TYPE_MAP[entry['type']][0],
                                                                   url=entry['url'],
                                                                   text=title,
                                                                   author=entry['author'],
                                                                   timestamp=entry['datetime'].timestamp())


class DolphinBot:
    def __init__(self, slack_hook_url, op_atom_url, repetitions_allowed=False, check_interval=5):
        self._check_interval = check_interval
        self.repetitions_allowed = repetitions_allowed

        self._slack = SlackConnection(slack_hook_url)
        self._op_activities = OpenProjectActivities(op_atom_url)
        self._run()

    def _run(self):
        logging.info("Watching for changes now in Atom activity feed...")
        old_entry = None
        while True:
            newest_entries = self._op_activities.deliver_updates()
            if newest_entries:
                logging.info("[!] Found total of %i changes.", len(newest_entries))
                for entry in newest_entries:
                    if self.repetitions_allowed:
                        self._slack.post(self._slack.build_json(entry))
                    elif old_entry is None or \
                            (old_entry is not None and not self._are_entries_equal(old_entry, entry)):
                        self._slack.post(self._slack.build_json(entry))
                    old_entry = entry

            time.sleep(self._check_interval)

    @staticmethod
    def _are_entries_equal(e1, e2):
        for test in ('title', 'author'):
            if e1[test] != e2[test]:
                return False
        return True

DolphinBot(SLACK_INCOMING_HOOK_URL, OPENPROJECT_ACTIVITY_ATOM_URL)
