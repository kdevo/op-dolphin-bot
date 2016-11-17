""" OP-Projects-List

! External dependency "requests" needed

Tiny utility that lists projects in OpenProject by using a trial and error method (brute force).
Why? The API of OP doesn't seem to provide a method to list existing projects, so this is a workaround.
In this project, it is used to easily find the project ID for the Dolphin Bot.

It also shows how to use basic auth to access the OpenProject API.
"""

import time
import requests
import json

# START CONFIGURATION
OP_BASE_URL = "YOUR OPENPROJECT URL"
OP_API_KEY = "YOUR API KEY"
# END CONFIGURATION


def show_projects(op_url, api_key, from_id=0, to_id=10, sleep=0.001):
    for i in range(from_id, to_id + 1):
        req = requests.get(op_url + "/api/v3/projects/" + str(i), auth=("apikey", api_key))
        if req.status_code == 200:
            req_dict = json.loads(str(req.content, 'utf8'))
            print('{0} ({1})'.format(req_dict['name'], req_dict['identifier']), '-> ID:', req_dict['id'])
        time.sleep(sleep)

show_projects(OP_BASE_URL, OP_API_KEY, 0, 50)

