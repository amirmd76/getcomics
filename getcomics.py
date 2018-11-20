#!/usr/bin/env python
import base64
import json
import subprocess
import time
import uuid
from _sha256 import sha256

import requests
from bs4 import BeautifulSoup

BASE = "https://getcomics.info/go.php-url=/"


def get_ext(link):
    DEFAULT = 'cbr'
    rl = link[::-1]
    dot = rl.find('.')
    if not dot:
        return DEFAULT
    e = rl[:dot]
    if len(e) < 1 or len(e) > 4:
        return DEFAULT
    return e[::-1]


def get_links(page):
    print("Inspecting page {}".format(page))
    with requests.get('https://getcomics.info/page/{}'.format(page)) as r:
        if r.status_code == 404:
            return None
        soup = BeautifulSoup(r.content, 'html.parser')
    divs = soup.find_all('div', attrs={"class": "post-header-image"})
    res = []
    seen = set([])
    for div in divs:
        for c in div.children:
            try:
                if c.name == 'a':
                    link = str(c.attrs['href'])
                    with requests.get(link) as r:
                        scur = BeautifulSoup(r.content, 'html.parser')
                        h2s = scur.find_all('h2')
                        name = ""
                        catgs = []
                        if h2s:
                            for i in range(1, len(h2s)-1):
                                h = h2s[i].text
                                h = h.replace("Free", "").replace("Download", "").strip()
                                if h:
                                    catgs.append(h)
                        h1s = scur.find_all('h1')
                        if h1s:
                            name = str(h1s[0].text).strip()
                        for elem in scur.find_all('a',
                                                  attrs={'class': 'aio-red'}):
                            attrs = elem.attrs
                            if 'href' in attrs:
                                href = attrs['href']
                                try:
                                    if not str(href).startswith(BASE) or not "Download Now" in elem.text:
                                        continue
                                    dl_link = base64.b64decode(
                                        attrs['href'][len(BASE):]).decode()
                                    if dl_link in seen:
                                        continue
                                    seen.add(dl_link)
                                    print("Got download link for {}".format(name))
                                    res.append({"link": dl_link, "name": name, "cat": catgs})
                                except:
                                    pass

            except:
                pass
    return res


DB = {}


def open_db():
    global DB
    try:
        with open("db.json", "r+") as f:
            DB = json.load(f)
    except:
        pass
    DB.setdefault("links", [])
    DB.setdefault("filenames", {})
    DB.setdefault("comics", {})


def save_db():
    with open("db.json", "w+") as f:
        json.dump(DB, f)


open_db()


def have_seen(links):
    if links is None:
        return True
    for link in links:
        if link["link"] not in DB["links"]:
            return False
    return True


def download_link(link):
    if have_seen([link]):
        return

    while True:
        hl = link["link"]
        default = sha256(hl.encode())[:32]
        filename = DB["filenames"].get(hl, default + "." + get_ext(hl))
        name = link["name"]
        DB["filenames"][hl] = filename
        link.update({"downloaded": False})
        DB["comics"][filename] = link
        print("Downloading {}...".format(name))
        status = subprocess.call(["bash", "dl.sh", hl, filename])
        if status == 0:
            DB['links'].append(hl)
            link.update({"downloaded": True})
            DB["comics"][filename] = link
            print("Successfully downloaded {} :D".format(name))
            return
        else:
            save_db()
            print("Retrying download {}...".format(name))
            time.sleep(10)


while True:
    try:
        cur = 1
        links = get_links(1)
        if have_seen(links):
            for i in list(range(12))[::-1]:
                p = 1 << i
                if have_seen(get_links(cur + p)):
                    cur += p
            cur += 1
        while True:
            links = get_links(cur)
            for link in links:
                download_link(link)
                save_db()
            if links is None:
                save_db()
                print("NOTHING TO DO!!!!")
                time.sleep(1200)
                break
    except Exception as e:
        print("EXCEPTION")
        print(str(e))
        print("WIRING TO DB")
        save_db()
        print("WROTE_TO_DB")
        raise e
