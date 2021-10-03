usage: link_scraper.py [-h] [-v [N]] [-f {treeview,grepable}] [-s] [--line-buffered] URL

Scrape links recursively given an URL

positional arguments:
  URL                   Root url from where to start scraping

optional arguments:
  -h, --help            show this help message and exit
  -v [N], --verbosity [N]
                        Configures the verbosity. 0 to be quiet, 1 for a standard verbosity, 2 for a more detailed verbosity. Default 0
  -f {treeview,grepable}, --format {treeview,grepable}
                        Choose how to print all the links (option grepable is useful is the script is used in pipe). Default "treeview"
  -s, --statistics      Print also info about elapsed time and other details. Default "false"
  --line-buffered       Show results as fast as possible. Not recommended to be used in pipe. Default "false"