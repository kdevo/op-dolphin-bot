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

        logging.debug("Trying to initially load Atom feed: %s", self._atom_url)
        if not self._refresh_xml_entries():
            # There is no implemented way to handle an invalid connection at startup.
            # Yes, we could do a "retry-strategy", but it makes no sense to start the bot without internet access.
            raise urllib.request.URLError("Critical: Initial update failed. Check your internet connection.")

        # We refreshed the XML entries above initially.
        # Those entries are excluded from the first call of "deliver_updates" by marking the entries as delivered:
        self._last_deliver_time = self._update_time  # append for testing purposes: "- timedelta(minutes=200)"

    def deliver_updates(self):
        result = []
        # Only if refreshing is successful:
        if self._refresh_xml_entries():
            # If there are new items:
            if self._last_deliver_time < self._update_time:
                logging.info("Got updates, update time: %s", self._update_time)
                for entry in self._xml_entries:
                    # Only append the newest items:
                    if self._last_deliver_time < self._convert_time(entry):
                        result.append(self._build_entry(entry))
                self._last_deliver_time = self._update_time
        return result

    def _refresh_xml_entries(self):
        try:
            with urllib.request.urlopen(self._atom_url) as atom_file:
                root = ElemTree.fromstring(atom_file.read().decode('utf8'))
            self._update_time = self._convert_time(root)
            if self._last_deliver_time is not None and self._update_time > self._last_deliver_time:
                self._xml_entries = root.findall('feed:entry', self._PREFIX)
            return True
        except urllib.request.HTTPError as http_err:
            logging.error("Error while executing HTTP request to OpenProject (Status: %i). "
                          "More info: %s", http_err.code, http_err)
            return False
        except urllib.request.URLError as url_err:
            logging.error("Unable to read from OpenProject. Probably not connected to the internet or wrong URL."
                          " More info: %s", url_err)
            return False

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
                if name in p and index < p[0]:
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
        return "{base}/projects/{id}/activity?{filter}" \
            .format(base=self.base_url, id=self.project_id, filter=self._get_filter_str(activity_filters))

    def build_activity_atom_url(self, rss_key, activity_filters=None):
        return "{base}/projects/{id}/activity.atom?key={key}&{filter}" \
            .format(base=self.base_url, id=self.project_id, key=rss_key, filter=self._get_filter_str(activity_filters))

    @staticmethod
    def part_to_text(url_part):
        return url_part.replace('_', ' ').capitalize()
