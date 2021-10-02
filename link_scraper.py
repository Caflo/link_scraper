import logging, telegram
import asyncio
import timeit
import sys
import json
import os, subprocess
import http.client
from io import StringIO
import requests
import os.path
from bs4 import BeautifulSoup
import re
from urllib.request import urlopen
from urllib.parse import urlparse


def analyze_anchors(url, base_url, result=[], verbose=False, indent_level=0):
    # curl with -L option makes curl following redirection. Useful for sites that redirect you to a landing page
    # -s option to hide progress 
    curl_cmd = f"curl -s -L {url}"  #TODO set user agent etc.
    page = None

    # check if curl is successful
    try:
        page = subprocess.check_output(curl_cmd, encoding="437")
    except subprocess.CalledProcessError as e:
        print(e.output)
        if e.output.startswith('error: {'):
            error = json.loads(e.output[7:]) # Skip "error: "
            print(error['code'])
            print(error['message'])
            return

    # scraping page
    soup = BeautifulSoup(page, features="html.parser")
    anchors = soup.findAll('a')
    if not anchors: # base case of recursion, end
        return
    for anchor in anchors:
        if anchor.has_attr('href'):
            next_url = anchor.attrs['href']
            if next_url in result: # skip duplicate links
                continue
            else:
                result.append(next_url)
                if next_url.startswith('/'): # keep navigating inside the target's page
                    next_url = base_url + next_url  # rewriting from relative to absolute path to make the curl work at the next recursion
                    if verbose:
                        print('\t' * indent_level + "|" + next_url)
                    result.append(next_url + " - INTERNAL")
                    analyze_anchors(next_url, base_url, result=result, verbose=verbose, indent_level=indent_level+1)
                else: # TODO for all non-local URLs, only collecting data 
                    if verbose:
                        print('\t' * indent_level + "|" + next_url)
                    result.append(next_url + " - EXTERNAL")
                    continue
        else: # skip anchors with no links
            continue

def link_scrape(url, verbose=False):
    result = dict()
    list = []

    # collecting statistics
    start_time = timeit.default_timer()
    result['data'] = analyze_anchors(url, url, result=list, verbose=verbose)
    end_time = timeit.default_timer()

    result['exec_time'] = end_time - start_time

    if verbose:
        print(f"Execution time: {result['exec_time']} seconds")

    return result
  
if __name__ == "__main__":
#    test_curl("localhosts")
    result = link_scrape(sys.argv[1], verbose=True)