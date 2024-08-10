# This script pulls out the body of a post
# and fixes it up so it can go in the RSS feed
import os.path
import sys

from html.parser import HTMLParser


class BodyGetter(HTMLParser):
    _want = False

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
                            v = f"https://nsrip.com/posts/{basename}{v}"
                        else:
                            v = f"https://nsrip.com/posts/{v}"
                        attrs[i] = (k, v)
            a = " ".join(f"{k}=\"{v}\"" for k, v in attrs)
            print(f"<{tag} {a}>", end="")

    def handle_endtag(self, tag):
        if self._want:
            if tag == "body":
                self._want = False
                return
            print(f"</{tag}>", end="")

    def handle_data(self, data):
        if self._want:
            print(data, end="")

    def handle_entityref(self, name):
        if self._want:
            print(f"&{name};", end="")

    def handle_charref(self, name):
        if self._want:
            print(f"&#{name};", end="")


parser = BodyGetter(convert_charrefs=False)
basename = os.path.basename(sys.argv[1])
with open(sys.argv[1]) as f:
    parser.feed(f.read())
