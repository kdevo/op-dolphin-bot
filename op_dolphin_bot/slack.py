import urllib.request
import time
import random
import logging
import re
import json
from string import Template
from datetime import datetime, timezone

from .constants import PROGRAM_NAME, PROGRAM_VERSION, GITHUB_URL
from .open_project import OpenProjectURL


class SlackConnection:
    """ Used for posting messages to Slack """

    def __init__(self, url_hook, max_retries=5, wait_on_fail=5):
        self.url_hook = url_hook
        self.max_retries = max_retries
        self.wait_on_fail = wait_on_fail
        logging.debug("Created a SlackConnection to %s.", self.url_hook)

    def post(self, json_message):
        retries = 0
        is_sent = False
        while not is_sent and (self.max_retries is None or retries <= self.max_retries):
            if retries > 0:
                logging.info("Retry #%i.", retries)
            logging.debug('Message posting in progress. Connecting to Slack for POST request.')
            request = urllib.request.Request(self.url_hook, headers={'Content-type': "application/json"})
            try:
                with urllib.request.urlopen(request, bytes(json_message, 'utf8')) as resp:
                    resp = resp.read().decode('utf8')
                    logging.debug("Response: %s.", resp.upper())
                is_sent = True
            except urllib.request.HTTPError as http_err:
                logging.error("Error while executing HTTP request to Slack (Status: %i). "
                              "More info: %s", http_err.code, http_err)
                retries += 1
                time.sleep(self.wait_on_fail)
            except urllib.request.URLError as url_err:
                logging.error("Unable to connect to Slack. Probably not connected to the internet or wrong URL."
                              " More info: %s", url_err)
                retries += 1
                time.sleep(self.wait_on_fail)


class SlackMessageBuilder:
    """ Used to build formatted Slack messages for the bot in JSON format """

    # Message with a single attachment ($vars need to be substituted by using build_json method)
    SINGLE_MESSAGE = \
        {
            'username': PROGRAM_NAME,
            'icon_emoji': ":dolphin:",
            'attachments': [{
                'title': "$type_emoji $type (Single Update)",
                'color': "#$color",
                'text': "<$title_url|➜ $text>",
                'fields':
                    [{
                        'title': "Author",
                        'value': "$author",
                        'short': False
                    }],
                'ts': '$timestamp',
                'footer': "<{0}|{1} {2}>".format(GITHUB_URL, PROGRAM_NAME, PROGRAM_VERSION),
                'mrkdwn_in': ['text']
            }]
        }

    # Message consisting of multiple parts/attachments
    SUMMARIZED_MESSAGE = \
        {
            'username': PROGRAM_NAME,
            'icon_emoji': ":dolphin:",
            'text': "$pre_praise Recorded a total of $changes changes in the last $minutes minutes "
                    "<$base_url|@OpenProject>. Summary:",
            'attachments': [{
                'title': "$type_emoji $type ($type_counter)",
                'title_link': '$activities_filtered_url',
                'fallback': "$type_counter new changes for $type.",
                'color': "#$color",
                'text': "$text",
                'fields': [
                    {
                        'title': "Author(s)",
                        'value': "$authors",
                        'short': False
                    }
                ],
                'mrkdwn_in': ['text']
            }]
        }

    # Maps the types to a tuple with emoji [0] and color [1] (will replace $type_emoji and $color)
    _TYPE_MAP = {
        None: (':coffee:', '00b7c3'),
        'work_packages': (':package:', '00b7c3'),
        'news': (':newspaper:', '248c15'),
        'wiki': (':book:', '11696d'),
        'documents': (':page_facing_up:', '681793'),
        'meetings': (':calendar:', 'e0283a'),
        'cost_objects': (':moneybag:', 'e0d01d'),
        'time_entries': (':watch:', 'a58747')
    }

    # "Maps" counted changes c to praise (will replace $pre_praise in _MULTI_PART_MESSAGE).
    # The last matched lambda expression will be used (so, the default is "Hi." - lambda expression is always True).
    _TEXT_PRAISE = [
        (lambda c: True, "Hi."),
        (lambda c: c > 2, "Cool."),
        (lambda c: c > 6, "Nice."),
        (lambda c: c > 10, "Wow. :star:"),
        (lambda c: c >= 12, "Huzzah! :star2:"),
        (lambda c: c >= 12 and random.randint(0, 1) == 1, "Huzzah! :heart_eyes:"),
        (lambda c: c >= 14 and 6 > datetime.now().hour >= 0, "Thank you night owl! :full_moon_with_face:")
    ]
    _FORMAT_ITALIC = ('New', 'In progress', 'Closed', 'On hold', 'Permanent', 'Rejected',  # Status
                      'Task', 'Phase', 'Milestone', 'Release', 'Feature', 'Bug')           # Other keywords
    _FORMAT_BOLD = ()  # '#[0-9]*' will print e.g. '#12' in bold

    def __init__(self, op_url_builder, max_titles_per_type=3, highlight_keywords=True):
        self._max_titles_per_type = max_titles_per_type
        self.highlight_keywords = highlight_keywords
        self._op_url_builder = op_url_builder

    def build_single_message(self, entry):
        return Template(json.dumps(self.SINGLE_MESSAGE)) \
            .safe_substitute(type=OpenProjectURL.part_to_text(entry['type']),
                             type_emoji=self._TYPE_MAP[entry['type']][0],
                             color=self._TYPE_MAP[entry['type']][1],
                             title_url=entry['url'],
                             text=self._highlight_text(entry['title']),
                             author=entry['author'],
                             timestamp=entry['datetime'].timestamp())

    def build_multi_part_message(self, entries, list_format="<{url}|➜> {title}\\n"):
        if len(entries) < 1:
            return
        type_info = {}
        first_entry_time = entries[0]['datetime']
        for entry in entries:
            if type_info.get(entry['type']) is None:
                type_info[entry['type']] = {}
                type_info[entry['type']]['count'] = 1
                type_info[entry['type']]['authors'] = {}
                type_info[entry['type']]['authors'][entry['author']] = 1
                if type_info[entry['type']]['count'] <= self._max_titles_per_type:
                    type_info[entry['type']]['attachment_text'] = \
                        list_format.format(url=entry['url'], title=entry['title'])
            else:
                type_info[entry['type']]['count'] += 1
                if type_info[entry['type']]['authors'].get(entry['author']) is None:
                    type_info[entry['type']]['authors'][entry['author']] = 1
                else:
                    type_info[entry['type']]['authors'][entry['author']] += 1
                if type_info[entry['type']]['count'] <= self._max_titles_per_type:
                    type_info[entry['type']]['attachment_text'] += \
                        list_format.format(url=entry['url'], title=entry['title'])
        attachments = []
        for t in type_info:
            authors_text = ""
            authors = type_info[t]['authors']
            for author in enumerate(authors):
                author_changes = type_info[t]['authors'][author[1]]
                if author[0] < (len(authors)-1):
                    authors_text += '{0} ({1}%), '.format(author[1], int(100/len(entries)*author_changes))
                else:
                    authors_text += '{0} ({1}%).'.format(author[1], int(100/len(entries)*author_changes))
            # BEGIN OF INEFFICIENCY
            if type_info[t]['count'] > self._max_titles_per_type:
                type_info[t]['attachment_text'] += " ..."
            attachment_json = Template(json.dumps(self.SUMMARIZED_MESSAGE['attachments'][0])) \
                .safe_substitute(type=OpenProjectURL.part_to_text(t),
                                 type_counter=type_info[t]['count'],
                                 type_emoji=self._TYPE_MAP[t][0],
                                 color=self._TYPE_MAP[t][1],
                                 text=self._highlight_text(type_info[t]['attachment_text']),
                                 activities_filtered_url=self._op_url_builder.build_activity_url((t,)),
                                 authors=authors_text)
            attachments.append(json.loads(attachment_json))
            # the message dict has been 1.) dumped/serialized to perform a substitution,
            # then 2.) deserialized to append the - now substituted - attachment. Not a big problem, but worth a note.
            # END OF INEFFICIENCY
        message = self.SUMMARIZED_MESSAGE.copy()
        message['attachments'] = attachments
        praise = None
        for condition in enumerate(self._TEXT_PRAISE):
            if condition[1][0](len(entries)):
                praise = condition[1][1]
        time_diff = (datetime.now(timezone.utc).astimezone(tz=None) - first_entry_time)
        return Template(json.dumps(message)).safe_substitute(changes=len(entries),
                                                             pre_praise=praise,
                                                             minutes=round(time_diff.seconds / 60, 1),
                                                             base_url=self._op_url_builder.base_url)

    def _highlight_text(self, text):
        if self.highlight_keywords:
            for kw in self._FORMAT_ITALIC:
                text = re.sub(kw, '_\g<0>_', text)
            for kw in self._FORMAT_BOLD:
                text = re.sub(kw, '*\g<0>*', text)
        return text
