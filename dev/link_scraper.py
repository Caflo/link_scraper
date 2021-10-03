import argparse
import timeit
import time
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

init(autoreset=True)

class colors:
    reset='\033[0m'
    bold='\033[01m'
    disable='\033[02m'
    underline='\033[04m'
    reverse='\033[07m'
    strikethrough='\033[09m'
    invisible='\033[08m'
    class fg:
        black='\033[30m'
        red='\033[31m'
        green='\033[32m'
        orange='\033[33m'
        blue='\033[34m'
        purple='\033[35m'
        cyan='\033[36m'
        lightgrey='\033[37m'
        darkgrey='\033[90m'
        lightred='\033[91m'
        lightgreen='\033[92m'
        yellow='\033[93m'
        lightblue='\033[94m'
        pink='\033[95m'
        lightcyan='\033[96m'
    class bg:
        black='\033[40m'
        red='\033[41m'
        green='\033[42m'
        orange='\033[43m'
        blue='\033[44m'
        purple='\033[45m'
        cyan='\033[46m'
        lightgrey='\033[47m'


class LinkScraper:

    def __init__(self, root_url, format='treeview', line_buffered=False, limit=0, no_color=False, interval=0) -> None:

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
        self.limit = limit
        self.iterations = 0
        self.interval = interval
        self.no_color = no_color


    def assoc_url_color(self, url):
        if url.netloc == self.root_url.netloc:
            if url.scheme == 'https':
                self.statistics['n_https'] += 1
                if self.no_color:
                    return ""
                else:
                    return colors.fg.lightgreen
            elif url.scheme == 'http':
                self.statistics['n_http'] += 1
                if self.no_color:
                    return ""
                else:
                    return colors.fg.yellow
        else:
            # don't care about insecure external links
            if self.no_color:
                return ""
            else:
                return colors.fg.lightgrey
        


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

        time.sleep(self.interval)

        # scraping page
        soup = BeautifulSoup(page, features="html.parser")
        anchors = soup.findAll('a')
        if not anchors: # base case of recursion, end
            return
        for anchor in anchors:
            if self.limit != 0 and self.iterations == self.limit:
                return


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
                    self.iterations += 1
                    url_colored_text = self.assoc_url_color(next_url)
                    if next_url.netloc == self.root_url.netloc:
                        self.statistics['n_internal_links'] += 1
                        self.tree_view += "|\t" * indent_level + "" + url_colored_text + next_url.geturl() + "\n"
                        if self.line_buffered:
                            if self.format == 'treeview':
                                print("|\t" * indent_level + "" + url_colored_text + next_url.geturl())
                            else:
                                print(url_colored_text + next_url.geturl())
                        self.analyze_anchors(next_url.geturl(), indent_level=indent_level+1)
                    else: 
                        self.statistics['n_external_links'] += 1
                        self.tree_view += "|\t" * indent_level + "" + url_colored_text + next_url.geturl() + "\n"
                        if self.line_buffered:
                            if self.format == 'treeview':
                                print("|\t" * indent_level + "" + url_colored_text + next_url.geturl())
                            else:
                                print(url_colored_text + next_url.geturl())
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
                if self.no_color:
                    print(f"{self.statistics['n_http']} internal links are not secure") 
                else:
                    print(colors.fg.orange + f"{self.statistics['n_http']} internal links are not secure") 
            else:
                if self.no_color:
                    print(f"No HTTP link was found") 
                else:
                    print(colors.fg.lightgreen + f"No HTTP link was found")


    def print_data(self, url, statistics=False):

        self.collect_link_statistics(url, statistics=statistics)

        if self.format == 'treeview' and not self.line_buffered:
            print(self.tree_view) 
        elif self.format == 'grepable' and not self.line_buffered:
            for link in self.links:
                print(self.assoc_url_color(url) + link.geturl())
        
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


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Scrape links recursively given an URL")
    parser.add_argument('url', metavar='URL', type=str, help='Root url from where to start scraping') 
    parser.add_argument('-f', '--format', dest='format', choices=['treeview', 'grepable'], default='treeview', help='Choose how to print all the links (option grepable is useful is the script is used in pipe). Default "treeview"') 
    parser.add_argument('-s', '--statistics', dest='statistics', action='store_true', default=False, help='Print also info about elapsed time and other details. Default "false"') 
    parser.add_argument('--line-buffered', dest='line_buffered', action='store_true', default=False, help='Show results as fast as possible. Not recommended to be used in pipe. Default "false"') 
    parser.add_argument('--limit', dest='N', action='store', type=int, default=0, help='Limit results to avoid excessive resource consumption') 
    parser.add_argument('-i', '--interval', dest='interval', action='store', type=int, default=0, help='Configures interval for curl to avoid making requests too fast. Default 0') 
    parser.add_argument('--no-color', dest='no_color', action='store_true', default=False, help='Disable colored output. Default "false"') 
    args = parser.parse_args()

    starting_url = args.url
    format = args.format
    line_buffered = args.line_buffered
    statistics = args.statistics
    limit = args.N
    interval = args.interval
    no_color = args.no_color

    link_scraper = LinkScraper(starting_url, format=format, line_buffered=line_buffered, limit=limit, no_color=no_color, interval=interval) 
    link_scraper.print_data(starting_url, statistics=statistics)