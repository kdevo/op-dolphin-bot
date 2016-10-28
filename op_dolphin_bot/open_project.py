from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ElemTree
import urllib.request
import logging


class OpenProjectActivities:
    """ Basically a tiny feed reader - it is used to read the OpenProject activities (atom feed) """

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
        self._last_deliver_time = self._update_time  # append for testing purposes: "- timedelta(minutes=300)"

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
    def guess_activity_type(url):
        """ Guesses the type (e.g. work_packages).
        First, the given URL is split into parts. Then, it is checked for type occurrences in the URL (file) path.
        The "rightmost" matching path part will the resulting type.

        Examples:
            ".../work_packages/21" -> will return "work_packages"
            ".../work_packages/21/time_entries" -> will return "time_entries", not "work_packages"!
        """
        parts = url.split("/")
        index = -1
        guessed = None
        for p in enumerate(parts):
            for name in OpenProjectURL.ACTIVITY_FILTERS:
                if name in p:
                    if index < p[0]:
                        guessed = p[1]
                        index = p[0]
        return guessed

    def _build_entry(self, xml_entry):
        entry = {}
        for kv in self._TAGS.items():
            entry[kv[1]] = xml_entry.find(kv[0], self._PREFIX).text
        entry['type'] = OpenProjectActivities.guess_activity_type(entry['url'])
        entry['datetime'] = self._convert_time(xml_entry)
        return entry

    def _convert_time(self, xml_entry, to_local_tz=True):
        # Assuming Zulu UTC (+0) military time zone in Atom feed, that's what the 'Z' stands for at the end:
        dt = datetime.strptime(xml_entry.find('feed:updated', self._PREFIX).text, "%Y-%m-%dT%H:%M:%SZ")
        if to_local_tz:
            return dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
        else:
            return dt


class OpenProjectURL:
    ACTIVITY_FILTERS = ('work_packages', 'wiki', 'news', 'documents', 'meetings', 'time_entries', 'cost_objects')

    def __init__(self, base_url, project_id):
        self.base_url = base_url
        self.project_id = project_id

    def _get_filter_str(self, activity_filters):
        if activity_filters is None:
            activity_filters = self.ACTIVITY_FILTERS
        filter_str = "apply=true"
        for f in activity_filters:
            filter_str += "&show_{0}=1".format(f)
        return filter_str

    def build_activity_url(self, activity_filters=None):
        return "{base}/projects/{id}/activity?{filter}"\
            .format(base=self.base_url, id=self.project_id, filter=self._get_filter_str(activity_filters))

    def build_activity_atom_url(self, rss_key, activity_filters=None):
        return "{base}/projects/{id}/activity.atom?key={key}&{filter}"\
            .format(base=self.base_url, id=self.project_id, key=rss_key, filter=self._get_filter_str(activity_filters))

    @staticmethod
    def part_to_text(url_part):
        return url_part.replace('_', ' ').capitalize()
