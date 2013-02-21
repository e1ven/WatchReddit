#!/usr/bin/env python3
#
# A quick and Dirty script to watch reddit for threads which interest me.

import collections
import json
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.parse
import urllib.error
import time
from smtplib import SMTP_SSL as SMTP   
from email.mime.text import MIMEText


class RedditScraper:
    def __init__(self):
        self.subreddits = set()
        self.headers =  {'User-agent':'Reddit Comment Watcher test by /u/e1ven; Version forked from Github'}
        self.nextcheck = {}
        self.nextglobal = 0
        self.interestingwords = ['reddit','tavern']
        self.commentswithtext = {}

    def MakeJSONReq(self,url):

        # Ensure we always wait until the next check is allowed.
        while self.nextglobal > time.time():
            time.sleep(1)
        # Ensure we only hit each specific URL once every 30 secs. If we ask early, wait.
        if url in self.nextcheck:
            while self.nextcheck[url] > time.time():
                time.sleep(1)

        # also set these waits at the end, so that if Reddit counts from competion, we're still on their good side.
        self.nextcheck[url] = time.time() + 30
        self.nextglobal = time.time() + 2

        try:
            f = urllib.request.urlopen(url)
            if f.getcode() == 200:
                # If we get a valid reply from Reddit, try to read it.
                response = f.read().decode('utf-8')
                f.close()
                respjson = json.loads(response, object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)
                return respjson
            else:
                return None
        except:
            print("Error pulling from Reddit")

        finally:
            self.nextcheck[url] = time.time() + 30
            self.nextglobal = time.time() + 2


    def UpdateSubredditList(self):
        # Start by getting the list of all subreddits
        api_url = "http://www.reddit.com/r/all/new.json?sort=new"
        req = urllib.request.Request(headers=self.headers,url=api_url)

        allstories = self.MakeJSONReq(url=api_url)
        for story in allstories['data']['children']:
            self.subreddits.add(story['data']['subreddit'])

    def CheckCommentsInSubreddit(self,subreddit):
        """
        Look for any interesting words, in any new comments, in a specified subreddit
        """

        if subreddit is not "all":
            api_url = "http://www.reddit.com/r/" + subreddit + "/comments.json"
        else:
            api_url = "http://www.reddit.com/comments.json"
        
        allcomments = self.MakeJSONReq(url=api_url)
        if allcomments == None:
            return
        for comment in allcomments['data']['children']:
            body = comment['data']['body']

            # Reddit gives weird linkids that don't match to URLs.
            # Reformat them back.
            linkid = comment['data']['link_id'].split("_", 1)[1]
            name = comment['data']['name'].split("_", 1)[1]
            permalink = "http://www.reddit.com/comments/" + linkid + "/SEOText/" + name
            for word in self.interestingwords:
                if word in body.lower():
                    if permalink not in self.commentswithtext:
                        self.commentswithtext[permalink] = body

    def SendMail(self):
        USERNAME = "you@gmail.com"
        PASSWORD = "YOURPASSWORD"
        SMTPserver = 'smtp.YOURSERVER.com'

        for permalink in self.commentswithtext:
            body = self.commentswithtext[permalink]
            if body[:12] !=  "ALREADY-SENT":
                content = "FYI - " + permalink + """
                """ + self.commentswithtext[permalink] + """

                Thanks!
                """
                content.encode('ascii', 'ignore')
                text_subtype = 'plain'
                msg = MIMEText(content, text_subtype)
                msg['Subject']=  "New Reddit Comment"
                msg['From']   = "YOUREMAIL" 

                conn = SMTP(SMTPserver)
                conn.set_debuglevel(False)
                conn.login(USERNAME, PASSWORD)
                try:
                    print("Sending Mail -- " + permalink)
                    conn.sendmail("YOU@YOUREMAIL.com", msg.as_string())
                finally:
                    conn.close()     

                # Mark that we've now sent this message      
                self.commentswithtext[permalink] = "ALREADY-SENT" + str(   int(time.time())   ) 
            else:
                timestamp = int(body[12:])
                # If this entry was added > 5 mins ago, remove it.
                if timestamp + 300 < int(time.time()):
                    del self.commentswithtext[permalink]
                    print("Removed old link - " + permalink)



r = RedditScraper()
#r.UpdateSubredditList()
while(1):
    r.CheckCommentsInSubreddit(subreddit='all')
    r.SendMail()


