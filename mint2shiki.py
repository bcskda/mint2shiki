#!/usr/bin/env python3

import sys, os, re
import sqlite3
import requests
import pyshiki

# Configurable:
Chromium_profile = 'Default'
Readers = ['mintmanga.com', 'readmanga.me', 'selfmaga.ru']
Langs = ['jp', 'en', 'ru'] # defines lang priority

def browser_histpath(profile):
    return "{}/.config/chromium/{}/History".format(os.getenv("HOME"), profile)

def reader_titlepage(url, host):
    expr = re.compile('http://{}/[^/]+'.format(host))
    match = re.match(expr, url)
    if match:
        return match.group()
    else:
        return ''

def reader_extract_titles(text):
    expr_any_prop = '( [a-z]{1,}=[\'\"].+?[\'\"]){0,}' # fixme
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
            if name[1] == 'original-':
                names['jp'] = name[3]
        return names
    else:
        print('Bug! while processing url')
        return None

if len(sys.argv) < 2:
    print('Usage: {} user [pass]'.format(sys.argv[0]))
    sys.exit(1)
Shiki_user = sys.argv[1]
if len(sys.argv) < 3:
    Shiki_pass = input('Password: ')
else:
    Shiki_pass = sys.argv[2]

browser_histfile = browser_histpath(Chromium_profile)
sql_conn = sqlite3.connect(browser_histfile)
sql_cursor = sql_conn.cursor()

sql_url_pattern = "http://{}/%/vol%/%"
sql_query = "SELECT url FROM urls WHERE urls.url LIKE '{}'".format(sql_url_pattern)
reader_title_urls = []
for host in Readers:
    try:
        sql_cursor.execute(sql_query.format(host))
    except Exception:
        print('Database locked - try closing browser')
        sql_conn.close()
        sys.exit(2)
    for match in sql_cursor.fetchall():
        reader_title_urls.append(reader_titlepage(match[0], host))
if not reader_title_urls:
    print("Nothing found in history - probably check browser profile name")
    sql_conn.close()
    sys.exit(0)
print('Urls:', reader_title_urls)

reader_titles = []
for url in reader_title_urls:
    title = reader_extract_titles(requests.get(url).text)
    if not title:
        print('Invalid reader page for {}'.format(url))
    else:
        reader_titles.append(title)
print('Titles:', reader_titles)

api = pyshiki.Api(Shiki_user, Shiki_pass)
shiki_uid = api.users('whoami').get()['id'] or None
if not shiki_uid:
    print('Authentication failed')
    conn.close()
    sys.exit(3)

shiki_title_ids = []
for title in reader_titles:
    title_id = None
    for lang in title:
        if title_id == None:
            search = api.mangas('search', q=title[lang]).get()
            if search:
                title_id = search[0]['id']
    if not title_id:
        print('Title \"', title[lang], '\" not found')
    else:
        shiki_title_ids.append(title_id)

shiki_failures = []
shiki_rate = {
    'user_id': shiki_uid,
    'target_type': 'Manga',
    'status': 'completed'
}
for id in shiki_title_ids:
    shiki_rate['target_id'] = id
    api_ret = api.user_rates(user_rate=shiki_rate).post()
    if not 'id' in api_ret:
        shiki_failures.append(id)
if shiki_failures:
    print('Failed to mark ids:', shiki_failures)
else:
    print('All {} titles marked as completed'.format(len(shiki_title_ids)))

sql_conn.close()
