import logging
import time

from .open_project import OpenProjectURL, OpenProjectActivities
from .slack import SlackConnection, SlackMessageBuilder


class DolphinBot:
    DEFAULT_FILTERS = ('work_packages', 'wiki', 'news', 'documents', 'meetings', 'cost_objects', 'time_entries')

    def __init__(self, slack_hook_url, op_base_url, op_project_id, op_atom_key, activity_filters=DEFAULT_FILTERS,
                 repetitions_allowed=False, check_sleep=90, smart_summary_trigger=2, max_links=7):
        """
        Creates a DolphinBot.

        :param slack_hook_url: URL of the incoming webhook for Slack
        :param op_base_url: Base URL for OpenProject
        :param op_project_id: Numeric ID for the project which activities should be tracked
        :param op_atom_key: RSS/Atom key (see Profile -> Tokens)
        :param check_sleep: Checks the feed every N seconds. The lower, the newer the messages posted in Slack.
                            This parameter also influences the smart summary feature (see below for an example)
        :param repetitions_allowed: If true, two entries after each other with the same content will be posted
        :param smart_summary_trigger: Automatically summarizes multiple new updates after N messages posted.
        :param max_links: Adds N links in the text field of the attachment when using the smart summary.

        Example scenarios of the smart summary feature (parameters have default values):
          (1) There is 1 new activity (entry) in 90 seconds
              -> post the change immediately using SINGLE_MESSAGE (see slack.SlackMessageBuilder)
          (2) There are 2 new activities in 90 seconds. They are held back another 90 seconds.
                * If there are changes again, repeat the above step.
                * Else, post all held back changes by using a SUMMARIZED_MESSAGE (see slack.SlackMessageBuilder).

        """
        self._check_sleep = check_sleep
        self.repetitions_allowed = repetitions_allowed
        self._smart_summary_limit = smart_summary_trigger
        self._max_links = max_links

        op_url_builder = OpenProjectURL(op_base_url, op_project_id)
        self._slack = SlackConnection(slack_hook_url)
        self._builder = SlackMessageBuilder(op_url_builder, self._max_links)
        self._op_activities = \
            OpenProjectActivities(op_url_builder.build_activity_atom_url(op_atom_key, activity_filters))

    def run(self):
        logging.info("Watching for changes now in Atom activity feed...")
        old_entry = None
        held_back_entries = []
        while True:
            newest_entries = self._op_activities.deliver_updates()
            # if there are any new entries:
            if newest_entries:
                logging.info("Found total of %i changes.", len(newest_entries))
                for entry in newest_entries:
                    # if repetitions are allowed or there are no repetitions:
                    if self.repetitions_allowed or \
                                    old_entry is None or (
                            old_entry is not None and not self._are_entries_equal(old_entry, entry)):
                        # if smart summary not active:
                        if not held_back_entries and len(newest_entries) < self._smart_summary_limit:
                            self._slack.post(self._builder.build_single_message(entry))
                        else:
                            held_back_entries.append(entry)
                    old_entry = entry
                if held_back_entries:
                    logging.warning("Smart summary Limit (%i) exceeded - holding back the new changes. "
                                    "Waiting another %i seconds...",
                                    self._smart_summary_limit, self._check_sleep)
            # elif there are any elements held_back_entries by the smart summary feature:
            elif held_back_entries:
                logging.info("Feed remained silent the last %i seconds, so we will post the summarized version.",
                             self._check_sleep)
                self._slack.post(self._builder.build_multi_part_message(held_back_entries))
                held_back_entries.clear()
            time.sleep(self._check_sleep)

    @staticmethod
    def _are_entries_equal(e1, e2):
        for test in ('title', 'author'):
            if e1[test] != e2[test]:
                return False
        return True
