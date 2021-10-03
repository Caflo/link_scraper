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
from enum import Enum
import matplotlib.pyplot as plt
import numpy as np

# TODO Add possibility to insert more than one domain, in case the site has multiple domains

init()

class UrlColors(Enum):
    URL_SECURE = 'green'
    URL_INSECURE = 'yellow'
    URL_EXTERNAL = 'white'

class LinkScraper:

    def __init__(self, root_url, format='treeview', line_buffered=False) -> None:

        if not root_url.startswith("http"):
            raise ValueError("Wrong URL format. Must be starting with \"http[s]://\"")

        self.root_url = urlparse(root_url)
        self.links = []
        self.tree_view = ""
        self.statistics = dict()
        self.statistics['n_internal_links'] = 0
        self.statistics['n_external_links'] = 0
        self.statistics['n_https'] = 0
        self.statistics['n_http'] = 0

        self.format = format
        self.line_buffered = line_buffered


    def assoc_url_color(self, url):
        if url.netloc == self.root_url.netloc:
            if url.scheme == 'https':
                self.statistics['n_https'] += 1
                return UrlColors.URL_SECURE.value
            elif url.scheme == 'http':
                self.statistics['n_http'] += 1
                return UrlColors.URL_INSECURE.value
        else:
            # don't care about insecure external links
            return UrlColors.URL_EXTERNAL.value
        


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
                    url_color = self.assoc_url_color(next_url)
                    if next_url.netloc == self.root_url.netloc:
                        self.statistics['n_internal_links'] += 1
                        self.tree_view += "|\t" * indent_level + "" + colored(next_url.geturl() + "\n", url_color)
                        if self.line_buffered:
                            if self.format == 'treeview':
                                print("|\t" * indent_level + "" + colored(next_url.geturl(), url_color))
                            else:
                                print(colored(next_url.geturl(), url_color))
                        self.analyze_anchors(next_url.geturl(), indent_level=indent_level+1)
                    else: 
                        self.statistics['n_external_links'] += 1
                        self.tree_view += colored("|\t" * indent_level + "" + next_url.geturl() + "\n", url_color)
                        if self.line_buffered:
                            if self.format == 'treeview':
                                print("|\t" * indent_level + "" + colored(next_url.geturl(), url_color))
                            else:
                                print(colored(next_url.geturl(), url_color))
                        continue


    def collect_link_statistics(self, url, statistics=False):
        
        time_before = datetime.now().strftime('%H:%M:%S')
        timer_start = timeit.default_timer()
        self.analyze_anchors(url)
        timer_stop = timeit.default_timer()
        time_after = datetime.now().strftime('%H:%M:%S')

        self.statistics['start_time'] = time_before
        self.statistics['end_time'] = time_after
        self.statistics['exec_time'] = timer_stop - timer_start
        total_links = self.statistics['n_internal_links'] + self.statistics['n_external_links']
        if total_links == 0:
            print("No statistics was possible because no link was found. Exiting")
            return
        
        if self.statistics['n_internal_links'] > 0 and self.statistics['n_external_links'] > 0:
            self.statistics['int_links_perc'] = self.statistics['n_internal_links'] / total_links
            self.statistics['ext_links_perc'] = self.statistics['n_external_links'] / total_links
        if statistics:
            print(f"Start time: {self.statistics['start_time']}\tEnd time: {self.statistics['end_time']}")
            print(f"Execution time: {self.statistics['exec_time']} seconds")
            if self.statistics['n_internal_links'] > 0 and self.statistics['n_external_links'] > 0:
                print(f"% internal links: {self.statistics['int_links_perc']:.2%}")
                print(f"% external links: {self.statistics['ext_links_perc']:.2%}")

            print(f"{self.statistics['n_https']} internal links are secure") 
            if self.statistics['n_http'] > 0:
                print(colored(f"{self.statistics['n_http']} internal links are not secure", UrlColors.URL_INSECURE.value)) 
            else:
                print(colored(f"No HTTP link was found", UrlColors.URL_SECURE.value)) 


            c1 = np.array([self.statistics['n_https'], self.statistics['n_http']])
            c1 = [value for value in c1 if value!=0]
            c1_labels = []
            if (self.statistics['n_https'] > 0):
                c1_labels.append('https')
            if (self.statistics['n_http'] > 0):
                c1_labels.append('http')


            c2 = np.array([self.statistics['n_internal_links'], self.statistics['n_external_links']])
            c2 = [value for value in c2 if value!=0]
            c2_labels = []
            if (self.statistics['n_internal_links'] > 0):
                c2_labels.append('internal links')
            if (self.statistics['n_external_links'] > 0):
                c2_labels.append('external links')

            fig, axes = plt.subplots(1, 2)

            p1 = axes[0].pie(c1, startangle=90, autopct='%1.1f%%')
            axes[0].legend(loc='lower left')
            axes[0].set_title('HTTP/HTTPS links')
            axes[0].legend(loc='best', labels=c1_labels)

            p2 = axes[1].pie(c2, startangle=90, autopct='%1.1f%%')
            axes[1].legend(loc='lower right')
            axes[1].set_title('Internal/external links')
            axes[1].legend(loc='best', labels=c2_labels)

            #draw circle
            centre_circle = plt.Circle((0,0),0.70,fc='white')
            fig = plt.gcf()
            fig.gca().add_artist(centre_circle)

            plt.tight_layout()
            plt.title('Link statistics')
            plt.show()

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
