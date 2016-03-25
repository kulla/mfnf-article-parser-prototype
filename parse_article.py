# -*- coding: utf-8 -*-

import re
import requests
import json

from lxml import etree

class Wiki:
    
    def __init__(self, domain):
        self.domain = domain

    def get_article(self, title):
        """ Get wikitext source of an article. """
        url = "https://" + self.domain + "/w/index.php"
        params = {
            "title": title,
            "action": "raw"
        }

        return requests.get(url, params = params).text

    def parse_text(self, text):
        """ Parse wikitext with Parsoid. """
        url = ("https://rest.wikimedia.org/" + self.domain 
               + "/v1/transform/wikitext/to/html")
        data = { "wikitext" : text }

        return requests.post(url, data=data).text

def xml_remove(old):
    """ Removes an xml tag. """
    old.getparent().remove(old)

def xml_replace(old, new):
    """ Replaces an xml tag with a new one. """
    new.tail = old.tail
    old.getparent().replace(old, new)

class MFNFSanitizer:

    def __init__(self, wiki):
        self.wiki = wiki

    def sanitize_templates(self, xml):
        while True:
            template = xml.find(".//*[@typeof='mw:Transclusion']")

            if template is not None:
                params = json.loads(template.get("data-mw"))
                aboutid= template.get("about")
                params = params["parts"][0]["template"]

                name = params["target"]["wt"].lower()
                name = name.replace(":mathe für nicht-freaks: vorlage:", "")

                new_xml = etree.Element("template", name=name)

                for pname, pvalue in params["params"].items():
                    param = etree.SubElement(new_xml, "param", name=pname)

                    pvalue = self.wiki.parse_text(pvalue["wt"])
                    pvalue = etree.fromstring(pvalue)[1]

                    param.extend(pvalue.getchildren())

                xml_replace(template, new_xml)
                
                for tag in xml.findall(".//*[@about='" + aboutid + "']"):
                    xml_remove(tag)
            else:
                break

        return xml

    def sanitize(self, text):
        """ Parse Wikitext from MediaWiki into clean XML. """

        # delete header and footer from wikitext
        text = re.sub(re.escape("{{#invoke:Mathe für Nicht-Freaks/Seite|")
                      + "(oben|unten)" + re.escape("}}"), "", text)

        # parse wikitext with Parsoid
        result = self.wiki.parse_text(text)

        # parse xml
        result = etree.fromstring(result)

        # handle templates
        result = self.sanitize_templates(result)

        # handle math tags
        for math_tag in result.findall(".//*[@typeof='mw:Extension/math']"):
            xml_replace(math_tag, etree.Element("math", tex=math_tag.get("alt")))

        # delete all id's
        for tag in result.findall(".//*[@id]"):
            del tag.attrib["id"]
    
        # return string of xml
        return etree.tostring(result, pretty_print=True, encoding=str)

class MFNF:

    def __init__(self):
        self.wiki = Wiki("de.wikibooks.org")
        self.sanitizer = MFNFSanitizer(self.wiki)

    def get_parsed_article(self, title):
        """ Parse Wikitext from MFNF into clean XML. """
        result = self.wiki.get_article(title)
        
        return self.sanitizer.sanitize(result)

if __name__ == "__main__":
    mfnf = MFNF()
    title = "Mathe für Nicht-Freaks: Äquivalenzrelation"
    result = mfnf.get_parsed_article(title)

    with open("article.xml", "w") as fd:
        fd.write(result)
