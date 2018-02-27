#!/usr/bin/env python3

import sys, os, re
import json
import sqlite3
import requests

def histpath(profile):
    return "{}/.config/chromium/{}/History".format(os.getenv("HOME"), profile)

def titlepage(url, host):
    expr = re.compile('http://{}/[^/]+'.format(host))
    match = re.match(expr, url)
    if match:
        return match.group()
    else:
        return ''

def extract_titles(text):
    expr_any_prop = '( [a-z]{1,}=[\'\"].+?[\'\"]){0,}' # any extra property in <span>
    expr = re.compile(
        '<span' + expr_any_prop
        + ' class=[\'\"](|eng-|original-)name[\'\"]'
        + expr_any_prop + '>'
        + '([\S\s]+?)</span>')
    match = re.findall(expr, text)
    if match:
        names = {}
        for name in match:
            if name[1] == '':
                names['ru'] = name[3]
            if name[1] == 'eng-':
                names['en'] = name[3]
            if name[1] == 'original':
                names['jp'] = name[3]
        return names
    else:
        print('Bug! while processing url')
        return {}

# Configurable:
Profile = "Profile 1"
Hosts = ["mintmanga.com", "readmanga.me"]

histfile = histpath(Profile)
conn = sqlite3.connect(histfile)
cursor = conn.cursor()

url_pattern = "http://{}/%/vol%/%"
query = "SELECT url FROM urls WHERE urls.url LIKE '{}'".format(url_pattern)
urls = []
for host in Hosts:
    print('Query:', query.format(host))
    cursor.execute(query.format(host))
    urls += [titlepage(match[0], host) for match in cursor.fetchall()]
if not urls:
    print("Nothing found in history - probably check profile name")
    conn.close()
    sys.exit(0)
print('Urls:', urls)

titles = [extract_titles(requests.get(url).text) for url in urls]
print('Titles:', titles)

# Now search shiki

conn.close()
