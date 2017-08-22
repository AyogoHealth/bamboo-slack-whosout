import json
import logging
import base64
import datetime
import re
import random

from urllib2 import Request, urlopen, URLError, HTTPError
from datetime import datetime
from datetime import timedelta

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

#
# Configure these variables for your environment
#

# The domain of your BambooHR account (uk or us)
BAMBOO_DOMAIN = "uk"

# Your BambooHR account name (the first part of your BambooHR url)
BAMBOO_ACCOUNT = "REDACTED"

# Your BambooHR API Key - note that if you use a personal API key generated from the
# BambooHR API and then run this code on AWS you are exposing all of the BambooHR data
# you can access to anybody who can view your Lambda code! Contact BambooHR support
# to get a specific API key for this purpose.
BAMBOO_API_KEY = "REDACTED"

# The incoming slack webhook to send messages to
SLACK_WEB_HOOK = "REDACTED"

# The slack channel to send messages to
SLACK_CHANNEL = "general"

# The colour for the slack message
SLACK_COLOUR = "#F3F300"

# Do not modify below here

base64string = base64.encodestring('%s:%s' % (BAMBOO_API_KEY, "x")).replace('\n', '')

bamboodomains = {
  "uk" : "api.bamboohr.co.uk",
  "us" : "api.bamboohr.com"
}

def whosout(today):
  out = []
  bamboorequest = Request("https://{0}/api/gateway.php/{1}/v1/time_off/whos_out/?filter=off&end={2}".format(bamboodomains[BAMBOO_DOMAIN], BAMBOO_ACCOUNT, today.strftime("%Y-%m-%d")))

  bamboorequest.add_header("Authorization", "Basic %s" % base64string)
  bamboorequest.add_header("Accept", "application/json")
  try:
    result = urlopen(bamboorequest)
    return json.loads(result.read())
  except HTTPError as e:
    logger.error("Request failed: %d %s", e.code, e.reason)
  except URLError as e:
    logger.error("Server connection failed: %s", e.reason)
  return out


def posttoslack(text):
  slack_message = {
    "attachments": [
      {
        "fallback": "Who's out?",
        "text": text,
        "mrkdwn_in": ["text"],
        "username": "bamboo-bot",
        "fields": [],
        "color": SLACK_COLOUR
      }
    ],
    "channel": SLACK_CHANNEL
  }

  req = Request(SLACK_WEB_HOOK, json.dumps(slack_message))
  try:
    response = urlopen(req)
    response.read()
    logger.info("Message posted to %s", slack_message['channel'])
  except HTTPError as e:
    logger.error("Request failed: %d %s", e.code, e.reason)
  except URLError as e:
    logger.error("Server connection failed: %s", e.reason)


def get_return_time_friendly(return_date):
  today_datetime_exact = datetime.today()
  today_datetime_date_only = datetime.strptime(today_datetime_exact.strftime("%Y-%m-%d"), "%Y-%m-%d")
  return_datetime = datetime.strptime(return_date, "%Y-%m-%d") + timedelta(days=1)
  days_difference_delta = return_datetime - today_datetime_date_only
  days_difference = days_difference_delta.days
  todays_week_number = today_datetime_exact.isocalendar()[1]
  return_week_number = return_datetime.isocalendar()[1]

  if days_difference == 1:
    return "tomorrow"
  elif todays_week_number == return_week_number:
    return return_datetime.strftime("%A")
  elif days_difference <= 7:
    return return_datetime.strftime("Next %A, %B %d")
  else:
    return return_datetime.strftime("%A, %B %d")


def holiday_to_emoji(name):
  if re.match('christmas', name, re.IGNORECASE):
    return ':christmas_tree:'
  if re.match('remembrance', name, re.IGNORECASE):
    return ':latin_cross:'
  if re.match('thanksgiving', name, re.IGNORECASE):
    return ':corn:'
  if re.match('canada day', name, re.IGNORECASE):
    return ':flag-ca:'
  if re.match('victoria day', name, re.IGNORECASE):
    return ':crown:'
  if re.match('good friday', name, re.IGNORECASE):
    return ':hatching_chick:'
  if re.match('family day', name, re.IGNORECASE):
    return random.choice([':man-woman-boy:', ':man-woman-girl:', ':man-woman-girl-boy:', ':man-woman-girl-girl:', ':man-woman-boy-boy:', ':woman-woman-boy:', ':woman-woman-girl:', ':woman-woman-girl-boy:', ':woman-woman-girl-girl:', ':woman-woman-boy-boy:', ':man-man-boy:', ':man-man-girl:', ':man-man-girl-boy:', ':man-man-girl-girl:', ':man-man-boy-boy:'])
  if re.match('new year', name, re.IGNORECASE):
    return ':confetti_ball:'
  return ':sparkles:'


def lambda_handler(event, context):
  today = datetime.now()

  out = whosout(today)

  if out:
    names = []
    for who in out:
      if who.get("type") == "holiday":
        posttoslack("The office is closed today for *{}* {}".format(who.get("name"), holiday_to_emoji(who.get('name'))))
        return
      else:
        names.append("{0} _(back {1})_".format(' '.join(who.get("name").split(',')[::-1]).strip(), get_return_time_friendly(who.get("end"))))

    if names:
      text = "*Who's out today:* \n{}".format('\n'.join(set(names)))
      posttoslack(text)
  #else:
  #  posttoslack("Nobody is out today! :tada:")


if __name__ == "__main__":
  lambda_handler(None, None)
