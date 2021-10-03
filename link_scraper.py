import argparse
import timeit
from datetime import datetime
import json
import subprocess
from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import ParseResult, urljoin, urlparse
from termcolor import colored
from colorama import init

#TODO Get statistics on how much http and https pages has a specific site
#TODO fix print on links that start with ./ (replace with CURRENT url, not the base one)

init()

class LinkScraper:

    def __init__(self, root_url, format='treeview', line_buffered=False) -> None:

        if not root_url.startswith("http"):
            raise ValueError("Wrong URL format. Must be starting with \"http[s]://\"")

        self.root_url = urlparse(root_url)
        self.links = []
        self.tree_view = ""
        self.n_internal_links = 0
        self.n_external_links = 0
        self.statistics = dict()

        self.format = format
        self.line_buffered = line_buffered


    def analyze_anchors(self, url, indent_level=0):
        # curl with -L option makes curl following redirection
        curl_cmd = f"curl -s -A \"Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/81.0\" -L \"{url}\"" 
        page = None

        # check if curl is successful
        try:
            page = subprocess.check_output(curl_cmd, shell=True, encoding="437")
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
                next_url = anchor.attrs['href'] # extract url
                next_url = urlparse(next_url)
                if not next_url.scheme: # if link has a relative local path, complete with the given scheme and domain name
                    # domain name is also needed because otherwise urlparse won't recognize it
                    next_url = ParseResult(scheme=self.root_url.scheme, netloc=self.root_url.netloc, path=next_url.path, \
                                                                            params=next_url.params, query=next_url.query, \
                                                                                                fragment=next_url.fragment)
                if next_url.path.startswith("./"):
                    parent = url[:url.rfind('/')]
                    abs_path = parent + next_url.path[1:]
                    next_url = urlparse(abs_path)

                if next_url in self.links: # skip duplicate links
                    continue
                else:
                    self.links.append(next_url) 
                    if next_url.netloc == self.root_url.netloc:
                        self.n_internal_links += 1
                        self.tree_view += "|\t" * indent_level + "" + colored(next_url.geturl() + "\n", 'green')
                        if self.line_buffered:
                            if self.format == 'treeview':
                                print("|\t" * indent_level + "" + colored(next_url.geturl(), 'green'))
                            else:
                                print(colored(next_url.geturl(), 'green'))
                        self.analyze_anchors(next_url.geturl(), indent_level=indent_level+1)
                    else: 
                        self.n_external_links += 1
                        self.tree_view += colored("|\t" * indent_level + "" + next_url.geturl() + "\n", 'white')
                        if self.line_buffered:
                            if self.format == 'treeview':
                                print("|\t" * indent_level + "" + colored(next_url.geturl(), 'white'))
                            else:
                                print(colored(next_url.geturl(), 'white'))
                        continue
#            else: # skip anchors with no links
#                continue


    def collect_link_statistics(self, url, statistics=False):
        
        time_before = datetime.now().strftime('%H:%M:%S')
        timer_start = timeit.default_timer()
        self.analyze_anchors(url)
        timer_stop = timeit.default_timer()
        time_after = datetime.now().strftime('%H:%M:%S')

        self.statistics['start_time'] = time_before
        self.statistics['end_time'] = time_after
        self.statistics['exec_time'] = timer_stop - timer_start
        total_links = self.n_internal_links + self.n_external_links
        if total_links == 0:
            print("No statistics was possible because no link was found. Exiting")
            return
        self.statistics['int_links_perc'] = self.n_internal_links / total_links
        self.statistics['ext_links_perc'] = self.n_external_links / total_links
        if statistics:
            print(f"Start time: {self.statistics['start_time']}\tEnd time: {self.statistics['end_time']}")
            print(f"Execution time: {self.statistics['exec_time']} seconds")
            print(f"Percent internal links: {self.statistics['int_links_perc']:.2%}")
            print(f"Percent external links: {self.statistics['ext_links_perc']:.2%}")


    def print_data(self, url, statistics=False):

        self.collect_link_statistics(url, statistics=statistics)

        if self.format == 'treeview' and not self.line_buffered:
            print(self.tree_view) 
        elif self.format == 'grepable' and not self.line_buffered:
            for link in self.links:
                print(link)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Scrape links recursively given an URL")
    parser.add_argument('url', metavar='URL', type=str, help='Root url from where to start scraping') 
    parser.add_argument('-v', '--verbosity', action='store', dest='N', nargs='?', default=0, help='Configures the verbosity. 0 to be quiet, 1 for a standard verbosity, 2 for a more detailed verbosity. Default 0') 
    parser.add_argument('-f', '--format', dest='format', choices=['treeview', 'grepable'], default='treeview', help='Choose how to print all the links (option grepable is useful is the script is used in pipe). Default "treeview"') 
    parser.add_argument('-s', '--statistics', dest='statistics', action='store_true', default=False, help='Print also info about elapsed time and other details. Default "false"') 
    parser.add_argument('--line-buffered', dest='line_buffered', action='store_true', default=False, help='Show results as fast as possible. Not recommended to be used in pipe. Default "false"') 
    args = parser.parse_args()

    starting_url = args.url
    format = args.format
    line_buffered = args.line_buffered
    statistics = args.statistics

    link_scraper = LinkScraper(starting_url, format=format, line_buffered=line_buffered) 
    link_scraper.print_data(starting_url, statistics=statistics)
