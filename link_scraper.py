import argparse
import timeit
from datetime import datetime
import json
import subprocess
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import urlparse


class LinkScraper:

    def __init__(self, root_url) -> None:

        if not root_url.startswith("http"):
            # TODO replace with valueerror
            raise ValueError("Wrong URL format. Must be starting with \"http[s]://\"")

        self.root_url = root_url
        self.links = []
        self.tree_view = ""
        self.n_internal_links = 0
        self.n_external_links = 0
        self.statistics = dict()


    def analyze_anchors(self, url, indent_level=0):
        # curl with -L option makes curl following redirection. Useful for sites that redirect you to a landing page
        # -s option to hide progress
        curl_cmd = f"curl -s -A \"Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/81.0\" -L {url}"  #TODO set user agent etc.
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
                if next_url in self.links: # skip duplicate links
                    continue
                else:
                    self.links.append(next_url) 
                    if next_url.startswith('/'): # keep navigating inside the target's page
                        next_url = self.root_url + next_url # rewriting from relative to absolute path to make the curl work at the next recursion
                        self.n_internal_links += 1
                        self.tree_view += "|\t" * indent_level + "" + next_url + "\n"
                        print("|\t" * indent_level + "" + next_url)
                        self.links.append(next_url + "  (INTERNAL)")
                        self.analyze_anchors(next_url, indent_level=indent_level+1)
                    else: # TODO for all non-local URLs, only collecting data 
                        self.links.append(next_url + "  (EXTERNAL)")
                        print("|\t" * indent_level + "" + next_url)
                        self.n_external_links += 1
                        self.tree_view += "|\t" * indent_level + "" + next_url + "\n"
                        continue
            else: # skip anchors with no links
                continue

    def analyze_anchors2(self, url, indent_level=0):
        # curl with -L option makes curl following redirection. Useful for sites that redirect you to a landing page
        # -s option to hide progress
        curl_cmd = f"curl -s -A \"Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/81.0\" -L {url}"  #TODO set user agent etc.
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
                if next_url in self.links: # skip duplicate links
                    continue
                else:
                    self.links.append(next_url) 
                    if next_url.startswith('/'): # keep navigating inside the target's page
                        next_url = self.root_url + next_url # rewriting from relative to absolute path to make the curl work at the next recursion
                        self.n_internal_links += 1
                        self.tree_view += "|\t" * indent_level + "" + next_url + "\n"
#                        print("|\t" * indent_level + "" + next_url)
#                        self.links.append(next_url)
                        self.analyze_anchors2(next_url, indent_level=indent_level+1)
                    else: # TODO for all non-local URLs, only collecting data 
#                        self.links.append(next_url)
#                        print("|\t" * indent_level + "" + next_url)
                        self.n_external_links += 1
                        self.tree_view += "|\t" * indent_level + "" + next_url + "\n"
                        continue
            else: # skip anchors with no links
                continue


    def collect_link_statistics(self, url):
        
        time_before = datetime.now().strftime('%H:%M:%S')
        timer_start = timeit.default_timer()
        self.analyze_anchors2(url)
        timer_stop = timeit.default_timer()
        time_after = datetime.now().strftime('%H:%M:%S')

        self.statistics['start_time'] = time_before
        self.statistics['end_time'] = time_after
        self.statistics['exec_time'] = timer_stop - timer_start
        total_links = self.n_internal_links + self.n_external_links
        self.statistics['int_links_perc'] = self.n_internal_links / total_links
        self.statistics['ext_links_perc'] = self.n_external_links / total_links
        if stdout:
            print(f"Start time: {self.statistics['start_time']}\tEnd time: {self.statistics['end_time']}")
            print(f"Execution time: {self.statistics['exec_time']} seconds")
            print(f"Percent internal links: {self.statistics['int_links_perc']:.2%}")
            print(f"Percent external links: {self.statistics['ext_links_perc']:.2%}")


    def scrape(self, url, format='treeview', stdout=True):

        self.collect_link_statistics(url)

        if format == 'treeview':
            print(self.tree_view) 
        else:
            for link in self.links:
                print(link)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Scrape links recursively given an URL")
    parser.add_argument('url', metavar='URL', type=str, help='Root url from where to start scraping') 
    parser.add_argument('-v', '--verbosity', action='store', dest='N', nargs='?', default=0, help='Configures the verbosity. 0 to be quiet, 1 for a standard verbosity, 2 for a more detailed verbosity. Default 0') 
    parser.add_argument('-f', '--format', dest='format', choices=['treeview', 'grepable'], default='treeview', help='Choose how to print all the links (grepable is useful is the script is used in pipe). Default "treeview"') 
    parser.add_argument('--no-stdout', dest='no_stdout', action='store_true', default=False, help='Do not print results on stdout if true. Default "false"') 
    args = parser.parse_args()

    starting_url = args.url
    format = args.format
    stdout = True
    if (args.no_stdout):
        stdout = False
    
    link_scraper = LinkScraper(starting_url) 
    link_scraper.scrape(starting_url, format=format, stdout=stdout)
