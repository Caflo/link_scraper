import logging, telegram
import asyncio
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

def analyze_anchors_local(base, domain_name):
    startpath = base + "\\example.html"
    filename = "example.html"
    regex = re.compile("^(http://{}|https://{}|/{})".format(domain_name, domain_name, domain_name))
    print(f"Starting from: {startpath}")
    print(f"Regex: {regex}")
    with open(filename, 'r') as f:
        contents = f.read()
    result_string = ""
    soup = BeautifulSoup(contents, features="html.parser")
    links = soup.find_all('a', {"href": regex})

    if not links:
        print(result_string)
    else:
        result_string += f"Link found in: {domain_name + '/' + filename}" + ':\n'
        for link in links:
            result_string += '\t' + link['href'] + '\n'
        result_string += '\n'
        analyze_anchors_local(base, domain_name) 

# same method but without memorizing list in a variable
def analyze_anchors(url, base_url, indent_level=0, list=[]):
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
            if next_url in list: # skip duplicate links
                continue
            else:
                list.append(next_url)
                if next_url.startswith('/'): # keep navigating inside the target's page
                    next_url = base_url + next_url  # rewriting from relative to absolute path to make the curl work at the next recursion
                    print('\t' * indent_level + next_url)
                    analyze_anchors(next_url, base_url, indent_level=indent_level+1, list=list)
                else: # TODO for all non-local URLs, collect data before continuing 
                    continue
        else: # skip anchors with no links
            continue

# TODO try pipes for share variables like indent_level to make the code more flexible and pretty
def link_scrape(url, base_url, result=[], indent_level=0, verbose=False):
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
                        print('\t' * indent_level + next_url)
                    result.append(next_url + " - INTERNAL")
                    link_scrape(next_url, base_url, result=result, indent_level=indent_level+1, verbose=verbose)
                else: # TODO for all non-local URLs, collect data before continuing 
                    next_url = base_url + next_url  # rewriting from relative to absolute path to make the curl work at the next recursion
                    result.append(next_url + " - EXTERNAL")
                    continue
        else: # skip anchors with no links
            continue

      

if __name__ == "__main__":
#    test_curl("localhosts")
    result = []
    link_scrape("localhost", "localhost", result, 0, True)
#    print('\n'.join(result))