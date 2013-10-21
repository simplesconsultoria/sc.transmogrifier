# -*- coding: utf-8 -*-
# Author: João S. O. Bueno

import ast
import base64
import json
import os
import re
import urllib

from cStringIO import StringIO
from collections import deque
from datetime import datetime
from unicodedata import normalize

from PIL import Image

from sc.transmogrifier.utils import BluePrintBoiler
from sc.transmogrifier.utils import blueprint
from sc.transmogrifier.utils import ThouShallNotPass, NothingToDoHere
from sc.transmogrifier.utils import normalize_url

from sc.transmogrifier import logger

@blueprint("sc.transmogrifier.utils.pick_images_from_content")
class PickImagesFromContent(BluePrintBoiler):
    """ Gets <img> reference from text bodies of content items

    Parses the item "text" field, and for any HTML image reference,
    retrieves it from the web* and put it as an item on the pipeline
    """
    # TODO: this blueprint is "hardcoded" to fetch referenced images
    # from a remte web site or a collective.jsonnify equiped plone site.
    # it sh0uld be refactored to allow for generic data-sources

    # TODO: refactor for new options setting style
    def set_options(self):
        self.from_types = set(x.strip() for x in
                           self.options.get("from_types", "").split(",")
                           if x)
        # If the types to act on are container types
        # enabling this will put the referenced image inside the
        # current item - else, its relative path will be kept
        self.embed_images = ast.literal_eval(self.options.get(
                                             "embed_images", "False"))
        # NB: embed_images will fail for ordinary Documents or news items
        # as it is intended to be used for folderidsh content types.
        # It is designed to work if the item will only become
        # folderish later on the pipeline,tough

        # Some of the images may have "resolveuid" links which
        # are redirected to the proper value by the source Plone site
        # (if it is the case)
        # Enabling this replaces redirected urls in the "SRC" attribute
        # of <img tags for the final value.
        self.replace_references = ast.literal_eval(self.options.get(
                                             "replace_references", "True"))
        self.source_prefix = self.options.get("source_prefix",
            "http://example.com/some_plone_site").strip().rstrip("/")
        # not used.
        self.load_external_images = False
        # Wormhole is a construct depending on
        # sc.transmogrifier.utils.whitehole blueprint
        # which makes forked items (int his case, fetcehd images)
        # appear earlier on the  pipeline instead of just
        # in the blueprints ahead of this
        self.use_wormhole = ast.literal_eval(self.options.get(
                                 "use_wormhole", "False"))
        self.use_jsonmigrator = ast.literal_eval(self.options.get(
                                 "use_jsonmigrator", "False"))

    def __iter__(self):
        self.seen_sections = set()
        for item in self.previous:
            images = []
            try:
                item, images = self.transmogrify(item)
            except NothingToDoHere:
                pass
            except ThouShallNotPass:
                continue
            yield item
            if not self.use_wormhole and images:
                for image in images:
                    yield image

    def transmogrify(self, item):
        path = self.get_path(item)
        text = item.get("text", u"")
        if not text:
            raise NothingToDoHere
        # One never knows how those json read
        # strings end up:
        if not isinstance(text, unicode):
            text = text.decode("utf-8")
        image_matches = re.finditer(ur"""<img.*?src\s*?=\s*?"(.*?)".*?>""", text,
                re.DOTALL | re.MULTILINE
                )
        images = []
        for match in reversed(list(image_matches)):

            # *** retrieve image URL and name data:

            start_tag, end_tag, img_title, rel_url, url = \
                    get_image_refs(match, path, self.source_prefix)

            if url == rel_url and not self.load_external_images:
                continue

            # *** retrieve remote image itself

            real_url, image, view_parts = get_remote_image(
                                           url, item, img_title,
                                           self.use_jsonmigrator)
            if real_url is None:
                continue

            image_filename = image["_filename"]

            # *** Fix image references in item's text html content:

            if real_url.startswith(self.source_prefix):
                img_path = real_url[len(self.source_prefix):]
            else: # the still-not-used external images case
                # FIXME: won't work for non folderish content types:
                img_path = path + "/" + url.rsplit("/")[-1]
            img_ref = img_path
            if self.embed_images:
                image["_orig_path"] = img_path
                img_path = path + "/" + image_filename
                img_ref = image_filename
                # Restore the reference to the
                # special view used in plone, after the
                # image file name:
                if view_parts:
                    img_ref += "/%s/" % ("/".join(view_parts))

            image["_path"] = img_path

            if self.replace_references and img_path != rel_url:
                img_ref_unicode = img_ref.decode("utf-8")
                # FIXME: For now, sc.transmgorgrifier
                # fix_path blueprint is not keeping
                # references in texts in sync
                # so, we assume it is being used on the pipeline
                # and normalize the url here
                # (should not affect well behaved urls anyway)
                img_ref_unicode = normalize_url(img_ref_unicode)
                text = text[:start_tag] + img_ref_unicode + text[end_tag:]

            # *** Set image to be put in the pipeline
            if self.use_wormhole:
                self.storage["wormhole"].push(image)
            else:
                images.append(image)
        item["text"] = text
        return item, images


def get_image_refs(match, path, source_prefix):
    # group is the text for whole expr., groups()[0] is the
    # text for the "src" tag
    rel_url_unicode = match.groups()[0]
    start_img, end_img = match.span()
    start_tag = start_img + match.group().find(rel_url_unicode)
    end_tag = start_tag + len(rel_url_unicode)
    rel_url = rel_url_unicode.encode("utf-8")
    if ":" in rel_url[:7]:
        url = rel_url

    else:
        if rel_url.startswith("/"):
            url = source_prefix + rel_url
        elif rel_url.startswith("resolveuid"):
            url = source_prefix + "/" + rel_url
        else:
            url = source_prefix + path + "/" + rel_url

    img_title = re.findall(ur"""alt\s*?=\s*?"(.*?)"[\s>]""",
                          match.group(), re.DOTALL|re.MULTILINE)

    img_title = img_title[0] if img_title else ""
    return  start_tag, end_tag, img_title, rel_url, url


def get_remote_image(url, item, img_title="", pathkey="_path",
                     jsonmigrator = False):

    # FIXME: not making an extra call to get the real pathkey
    logger.info("""Fetching image %s for article %s """ % (url,
            item.get(pathkey, "")))
    # Strip plone view from URL:
    url, it_worked = _strip_view(url)
    # it won't work if the image url does not have a proper image
    if not it_worked:
        jsonmigrator = False
    if jsonmigrator:
        url += "/get_item"
    try:
        http = urllib.urlopen(url)
        image_data = http.read()
        if http.code > 399:
            # we can't  get the image here
            raise IOError
        real_url = http.url

    except Exception as error:
        logger.error("Could not retrieve image at %s: %s - skipping" %
                     (url, error))
        return None, None, []

    if jsonmigrator and real_url.endswith("/get_item"):
            real_url = real_url[:len("/get_item")]
    image_filename, post_parts = _get_filename(real_url)

    if jsonmigrator:
        try:
            image = json.loads(image_data)
        except ValueError:
            logger.warn("Could not retrieve image json contents at %s " % url)
            raise None, None, []

    else: # build object item for the pipeline
        image = {}
        image["_type"] = "Image"
        image["image"] = image_data

        image["creation_date"] = item.get("creation_date", None)
        image["modification_date"] = item.get("modification_date", None)
        image["_transitions"] = item.get("_transitions", "published")

        if not img_title:
            img_title = image_filename.split(".")[0].encode("utf-8")
        image["title"] = img_title

    image["_filename"] = image_filename
    return real_url, image, post_parts

def _strip_view(url):
    """
    This is not designed for your mommy's URLs:
    # FIXME: factor out doctest to tests/

    >>> _strip_view("http://toras.tangrama.com.br:8081/revistadobrasil/resolveuid/2a7c53f180ae57ccf2c49496d3a5679e")
    ('http://toras.tangrama.com.br:8081/revistadobrasil/resolveuid/2a7c53f180ae57ccf2c49496d3a5679e', True)
    >>> _strip_view("http://toras.tangrama.com.br:8081/revistadobrasil/resolveuid/2a7c53f180ae57ccf2c49496d3a5679e/image_mini")
    ('http://toras.tangrama.com.br:8081/revistadobrasil/resolveuid/2a7c53f180ae57ccf2c49496d3a5679e', True)
    >>> _strip_view("http://toras.tangrama.com.br:8081/revistadobrasil/blabla.JPG/image_size/432x430")
    ('http://toras.tangrama.com.br:8081/revistadobrasil/blabla.JPG', True)
    >>> _strip_view("http://toras.tangrama.com.br:8081/revistadobrasil")
    ('http://toras.tangrama.com.br:8081/revistadobrasil', False)
    """ #noqa
    original = url
    it_worked = False
    p3 = ""
    while True:
        try:
            p1, p2 = url.rsplit("/", 1)
        except ValueError:
            return original, it_worked
        # FIXME: allow alternative for not named-as-file images
        if p2.rsplit(".",1)[-1].lower() in (
                "jpg", "jpeg", "gif", "png",
                "tif", "tiff", "bmp", "svg", "webp",
                ):
            it_worked = True
        elif p2.startswith("resolveuid"):
            url += "/" + p3
            it_worked = True
        if it_worked:
            return url, it_worked
        url = p1
        p3 = p2

def _get_filename(url):
    # In a plone site, there might be aditional
    # compontes in the path after the image name
    # (like /thumb, /image_slider, and so on)
    # FIXME: to whoever it pleases,
    # join the "_strip_view" and "_get_filename"
    # functions together. Not me, not today.
    # It is simpler than that, because
    # any "resolveuid" type url will already be
    # de-referenced when we get here.
    parts = url.split("/")
    post_parts = deque()
    for part in reversed(parts):
        if "." in part:
            return part, post_parts
        post_parts.appendleft(part)
    # F*ck!!!
    return parts[-1], deque()

@blueprint("sc.transmogrifier.utils.check_image")
class CheckImage(BluePrintBoiler):
    def transmogrify(self, item):
        if (not "image" in item):
            raise NothingToDoHere
        if isinstance(item["image"] , dict):
            data = item["image"]["data"]
        else:
            data = item["image"]
        try:
            data= StringIO(data)
            img = Image.open(data)
        except (TypeError, IOError) as error:
            # We caught it:  a fake image! :-)
            path = self.get_path(item)
            if item.get("_type", "") == "Image":
                logger.warn("Image at %s contains no image data - discarding"
                            % path)
                raise ThouShallNotPass
            logger.warn("Item at %s contains no image data - scrubbing"
                        " incorrecet data" % path)
            del item["image"]
        return item



