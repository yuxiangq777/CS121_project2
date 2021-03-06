import logging
import re
from urllib.parse import urlparse,urljoin
from corpus import Corpus
from lxml import html
from collections import defaultdict
logger = logging.getLogger(__name__)

class Crawler:
    """
    This class is responsible for scraping urls from the next available link in frontier and adding the scraped links to
    the frontier
    """

    def __init__(self, frontier):
        self.frontier = frontier
        self.corpus = Corpus()
        self.subdomain_dict= defaultdict(int)
        self.out_link_dict= defaultdict(int)
        self.valid_dict= defaultdict(int)
        self.downloaded = set()
        self.traps = defaultdict(set)
    def start_crawling(self):
        """
        This method starts the crawling process which is scraping urls from the next available link in frontier and adding
        the scraped links to the frontier
        """
        while self.frontier.has_next_url():
            url = self.frontier.get_next_url()
            logger.info("Fetching URL %s ... Fetched: %s, Queue size: %s", url, self.frontier.fetched, len(self.frontier))
            self.subdomain_dict[urlparse(url).hostname] +=1
            self.downloaded.add(url)
            url_data = self.fetch_url(url)

            for next_link in self.extract_next_links(url_data):
                if self.corpus.get_file_name(next_link) is not None:
                    if self.is_valid(next_link):
                        self.frontier.add_url(next_link)
                        self.out_link_dict[url] += 1
        analytics = open("analytics.txt","w")
        analytics.write("1. The subdomains this crawler visited and number of different URL it has processed from the associated subdomain:\n")
        for subdomain,count in self.subdomain_dict.items():
            analytics.write(subdomain+": "+str(count)+"\n")
        if len(self.out_link_dict) != 0:
            best_page= sorted(self.out_link_dict.items(),key=(lambda t:t[1]),reverse=True)[0]
            analytics.write("\n2.The page with the most valid out links is: "+best_page[0]+" with "+str(best_page[1])+" out links.\n")
        analytics.write("\n3.List of downloaded URL:\n")
        for d_url in self.downloaded:
            analytics.write(d_url+"\n")
        analytics.write("\nList of identified trap:\n")
        for description,trap_set in self.traps.items():
            analytics.write("\n"+description+": \n")
            for trap in trap_set:
                analytics.write(trap+"\n")
        analytics.close()
    def fetch_url(self, url):
        """
        This method, using the given url, should find the corresponding file in the corpus and return a dictionary
        containing the url, content of the file in binary format and the content size in bytes
        :param url: the url to be fetched
        :return: a dictionary containing the url, content and the size of the content. If the url does not
        exist in the corpus, a dictionary with content set to None and size set to 0 can be returned.
        """
        url_data = {
            "url": url,
            "content": None,
            "size": 0
        }
        file_name= self.corpus.get_file_name(url)
        if file_name!=None:
            file= open(file_name,"rb")
            url_data["content"] = file.read()
            url_data["size"] = len(url_data["content"])
            file.close()
        return url_data

    def extract_next_links(self, url_data):
        """
        The url_data coming from the fetch_url method will be given as a parameter to this method. url_data contains the
        fetched url, the url content in binary format, and the size of the content in bytes. This method should return a
        list of urls in their absolute form (some links in the content are relative and needs to be converted to the
        absolute form). Validation of links is done later via is_valid method. It is not required to remove duplicates
        that have already been fetched. The frontier takes care of that.

        Suggested library: lxml
        """
        outputLinks = []
        html_content= html.fromstring(url_data["content"])
        found_url=html_content.xpath('//a/@href')
        for found in found_url:
            outputLinks.append(urljoin(url_data["url"],found))
        return outputLinks

    def is_valid(self, url):
        """
        Function returns True or False based on whether the url has to be fetched or not. This is a great place to
        filter out crawler traps. Duplicated urls will be taken care of by frontier. You don't need to check for duplication
        in this method
        """
        parsed = urlparse(url)
        url_data= self.fetch_url(url)
        if url_data['size'] == 0 or ascii(url).strip("'") != url:
            self.traps["Fake url"].add(url)
            return False
        if parsed.scheme not in set(["http", "https"]):
            return False
        character_list= url.split("/")
        character_set= set(character_list)
        if len(character_list) != len(character_set):
            self.traps["Potential loop or repeat directories"].add(url)
            return False
        if len(parsed.query) > 0 and ".ics.uci.edu" in parsed.hostname:
            self.valid_dict[parsed.hostname+parsed.path] +=1
            if self.valid_dict[parsed.hostname+parsed.path] > 150:
                self.traps["Dynamic page or too many queries"].add(url)
                return False
            query_list = parsed.query.split("=")
            for e in query_list:
                if len(e)> 30:
                    self.traps["Dynamic page or too many queries"].add(url)
                    return False 
        
        try:
            
            return ".ics.uci.edu" in parsed.hostname \
                   and not re.match(".*\.(css|js|bmp|gif|jpe?g|ico" + "|png|tiff?|mid|mp2|mp3|mp4" \
                                    + "|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf" \
                                    + "|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1" \
                                    + "|thmx|mso|arff|rtf|jar|csv" \
                                    + "|rm|smil|wmv|swf|wma|zip|rar|gz|pdf)$", parsed.path.lower())

        except TypeError:
            print("TypeError for ", parsed)
            return False

