# coding: utf-8
# Author: Joao S. O. Bueno

import json
import urllib2

from sc.transmogrifier import logger

from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import normalize_url
from sc.transmogrifier.utils import NothingToDoHere, ThouShallNotPass


# TODO: grab authentication boilerplate from
# collective.jsonmigrator.catalogsource blueprints
#Ideally this one would be one of those, factored out
# (or move to use requests)
# meanwhile, as long as collective.jsonmigrator.catalogsource
# is on the pipeline and configured, it does install a proper urllib2 openner
# for the remote site, and we can get a ride on it.
# (if authentication is needed at all)


@blueprint("sc.transmogrifier.utils.remotefetcher")
class RemoteFetcher(BluePrintBoiler):

    def set_options(self):
        self.json_posfix = self.options.get("json_posfix", "get_item")
        # no need to set if the urls to fetch are complete.
        self.remote_url_prefix = self.options.get("remote_url_prefix", "")
        self.pop_path_prefix = int(self.options.get("pop_path_prefix", "0"))

    def transmogrify(self, item):
        if not "__remote_url_fetch" in item:
            raise NothingToDoHere
        remote_url = item["__remote_url_fetch"]

        remote_url += (("/" if remote_url[-1] != "/" else  "" ) +
                        self.json_posfix)
        if self.remote_url_prefix and ":" not in remote_url[:7]:
            remote_url =  (self.remote_url_prefix.rstrip("/") + "/"
                           + remote_url.lstrip("/"))
        try:
            logger.info("Fetching remote item at %s " % remote_url)
            new_item = json.loads(urllib2.urlopen(remote_url).read())
        except Exception as error:
            logger.error("Could not retrieve and decode remote item "
                          "at %s, skipping" % remote_url)
            raise ThouShallNotPass
        if self.pop_path_prefix and "_path" in new_item:
            pathcomps = new_item["_path"].lstrip("/").split("/")
            pathcomps = pathcomps[self.pop_path_prefix:]
            new_item["_path"] = "/" + "/".join(pathcomps)
        item.update(new_item)
        item.pop("__remote_url_fetch", "")
        return item

