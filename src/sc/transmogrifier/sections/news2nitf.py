# -*- coding: utf-8 -*-
# Author: João S. O. Bueno

import ast
import re

from unicodedata import normalize

from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import ThouShallNotPass, NothingToDoHere
from sc.transmogrifier.utils import transition_from_history

from sc.transmogrifier import logger

FROM_TYPES = ("News Item", "Blog Entry")
TO_TYPE = "collective.nitf.content"


def normalize_name(name):
    name = name.lower()
    # Remove accented chars
    if isinstance(name, unicode):
        name = normalize('NFKD', name).encode('ASCII', 'ignore')
    # and replace all non-dot, non-alphanumeric chars by "_"
    name = re.sub("[^a-z0-9\.]", "_", name)
    return name

@blueprint("sc.transmogrifier.utils.news2nitf")
class News2NITF(BluePrintBoiler):

    def set_options(self):
        self.nitf_language = self.options.get("nitf-language", "en")
        self.nitf_genre = unicode(self.options.get("nitf-genre",
                                  "Current"), "utf-8")
        self.nitf_section = unicode(self.options.get("nitf-section",
                                  ""), "utf-8")
        self.nitf_urgency = int(self.options.get("nitf-urgency", "0"))
        self.subtitle_from_description = ast.literal_eval(
            self.options.get("subtitle-from-description", "False"))
        self.pick_section_from_path = int(self.options.get(
                                      "section-from-path", "-1"))
        self.upload_prefix = self.options.get("upload_prefix", ""
                                             ).rstrip("/")
        self.section_names = ast.literal_eval(self.options.get(
            "section_names", """("Politics", "Society", "Opinion")"""))
        from_types = self.options.get("from_types", "")
        if from_types:
            self.from_types = [x.strip() for x in from_types.split(",") if x]
        else:
            self.from_types = FROM_TYPES

    def __iter__(self):
        self.seen_sections = set()
        for item in self.previous:
            image = None
            try:
                item, image = self.transmogrify(item)
            except NothingToDoHere:
                pass
            except ThouShallNotPass:
                continue
            yield item
            if image:
                yield image
        if self.seen_sections:
            with open("/tmp/seen_sections", "wt") as sections_file:
                for section in self.seen_sections:
                    sections_file.write(section + "\n")

    def transmogrify(self, item):
        typekey = self.typekey(*item.keys())[0]
        path = self.get_path(item)
        if self.upload_prefix:
            path = self.upload_prefix + path
            item["_path"] = path
        if not typekey or not item[typekey] in self.from_types:
            return item, None
        item[typekey] = TO_TYPE
        # Description in NITF should contain an abstract of the article
        # on the contents being moved it usually contains a subtitle
        if self.subtitle_from_description:
            item["subtitle"] = item.pop("description", u"")
        item["byline"] = item.get("creators", [u""])[0]
        item["genre"] = self.nitf_genre
        if self.pick_section_from_path != -1:
            section = path.split("/")[self.pick_section_from_path]
            item["section"] = section
        elif self.nitf_section:
            item["section"] = self.nitf_section
        elif item["_type"] == "Story":
            if not item.get("section", None) in self.SECTION_NAMES:
                item["section"] = u"Other"
            self.seen_sections.add(item["section"])

        item["urgency"] = self.nitf_urgency
        item["location"] = item.get("location", u"")
        item["subjects"] = item.get("subject", [])
        item["language"] = self.nitf_language

        # clears default page, since we are changing types
        # maybe add a configure option for this?
        item.pop("_defaultpage", None)

        transition_from_history(item)
        #fix_creators(item)
        logger.info("Converted item at %s to NITF" % path)

        image = {}
        if item.get("image", None) and item["image"].get("data", ""):
            image["_type"] = "Image"
            image["description"] = item.pop("imageCaption", u"")
            name = item["image"].get("filename", "")
            if not name:
                name = image.get("description", "image")[:15] + ".jpg"
            name = normalize_name(name).strip("_")
            image["_path"] = path + "/" + name
            transition_from_history(item)
            image["creation_date"] = item.get("creation_date", None)
            image["modification_date"] = item.get("modification_date", None)
            image["image"] = item["image"]["data"]
            del item["image"]
            logger.info("Yielding separate image for item at %s" % path)

        return item, image

