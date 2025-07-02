import os.path
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

# Use lxml to parse the feed because it supports CDATA sections
from lxml import etree


class BodyGetter(HTMLParser):
    def __init__(self, basename):
        super().__init__(convert_charrefs=False)
        self._want = False
        self._output = []
        self.basename = basename

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self._want = True
            return
        if self._want:
            # Fix up relative links
            key = None
            if tag == "img":
                key = "src"
            elif tag == "a":
                key = "href"
            if key:
                for i, (k, v) in enumerate(attrs):
                    if k == key and not v.startswith("http"):
                        if v.startswith("#"):
                            v = f"https://nsrip.com/posts/{self.basename}{v}"
                        else:
                            v = f"https://nsrip.com/posts/{v}"
                        attrs[i] = (k, v)
            a = " ".join(f'{k}="{v}"' for k, v in attrs)
            self._output.append(f"<{tag} {a}>")

    def handle_endtag(self, tag):
        if self._want:
            if tag == "body":
                self._want = False
                return
            self._output.append(f"</{tag}>")

    def handle_data(self, data):
        if self._want:
            self._output.append(data)

    def handle_entityref(self, name):
        if self._want:
            self._output.append(f"&{name};")

    def handle_charref(self, name):
        if self._want:
            self._output.append(f"&#{name};")

    def getvalue(self):
        return "".join(self._output)


class FirstElementGetter(HTMLParser):
    def __init__(self, tag, condition, convert_charrefs=False):
        super().__init__(convert_charrefs=convert_charrefs)
        self._want = False
        self._output = []
        self.tag = tag
        self.condition = condition
        self.value = None

    def handle_starttag(self, tag, attrs):
        if self.value is None and tag == self.tag and self.condition(attrs):
            self._want = True

    def handle_endtag(self, tag):
        if self._want and tag == self.tag:
            self._want = False
            self.value = "".join(self._output).strip()

    def handle_data(self, data):
        if self._want:
            self._output.append(data)

    def handle_entityref(self, name):
        if self._want:
            self._output.append(f"&{name};")

    def handle_charref(self, name):
        if self._want:
            self._output.append(f"&#{name};")


def get_post_content(post_path):
    # Read the file once
    with open(post_path, "r") as f:
        content = f.read()

    # Get the title
    title_parser = FirstElementGetter("title", lambda _: True)
    title_parser.feed(content)
    title = title_parser.value

    # Get the first paragraph for the summary
    summary_parser = FirstElementGetter(
        "p", lambda attrs: any(k == "summary" for k, v in attrs)
    )
    summary_parser.feed(content)
    summary = summary_parser.value

    # Get the body content using the existing getbody.py implementation
    basename = os.path.basename(post_path)
    body_parser = BodyGetter(basename)
    body_parser.feed(content)

    return title, summary, body_parser.getvalue()


def update_feed(feed_path, post_path):
    # Parse the post
    title, summary, content = get_post_content(post_path)

    # Parse the existing feed
    parser = etree.XMLParser(remove_blank_text=True, strip_cdata=False)
    tree = etree.parse(feed_path, parser=parser)
    root = tree.getroot()

    # Create new item
    item = etree.Element("item")

    # Add title
    title_elem = etree.SubElement(item, "title")
    title_elem.text = title

    # Add link
    link_elem = etree.SubElement(item, "link")
    link_elem.text = f"https://www.nsrip.com/posts/{post_path.name}"

    # Add description (first paragraph)
    desc_elem = etree.SubElement(item, "description")
    desc_elem.text = summary

    # Add pubDate (use current time with timezone abbreviation)
    pub_date = datetime.now().astimezone().strftime("%a, %d %b %Y %H:%M:%S %Z")
    pub_elem = etree.SubElement(item, "pubDate")
    pub_elem.text = pub_date

    # Add guid
    guid_elem = etree.SubElement(item, "guid")
    guid_elem.text = f"https://www.nsrip.com/posts/{post_path.name}"

    # Add content:encoded
    content_elem = etree.SubElement(
        item, "{http://purl.org/rss/1.0/modules/content/}encoded"
    )
    content_elem.text = etree.CDATA(content)

    # Find the channel and first item
    channel = root.find("channel")

    # Insert new item before the first existing item
    for index, child in enumerate(channel):
        if child.tag == "item":
            channel.insert(index, item)
            break
    else:
        # If no items exist, just append to channel
        channel.append(item)

    # Update lastBuildDate
    last_build = channel.find("lastBuildDate")
    if last_build is not None:
        last_build.text = pub_date

    # Write back to file with original namespace declarations
    tree.write(
        feed_path,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
        method="xml",
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: update_feed.py <feed.xml> <post.html>")
        sys.exit(1)

    feed_path = Path(sys.argv[1])
    if not feed_path.exists():
        print(f"Error: {feed_path} does not exist")
        sys.exit(1)

    post_path = Path(sys.argv[2])
    if not post_path.exists():
        print(f"Error: {post_path} does not exist")
        sys.exit(1)

    update_feed(feed_path, post_path)
