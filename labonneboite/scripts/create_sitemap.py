# coding: utf8

from datetime import datetime
import operator
import os
from flask import Flask, render_template
from flask_script import Manager
from slugify import slugify
from labonneboite.conf import settings
from labonneboite.common import geocoding

app = Flask(__name__)
manager = Manager(app)


@manager.command
def sitemap():
    """
    To rebuild the sitemap,
    simply run "make create_sitemap" and then commit the new sitemap.xml file.
    Currently you don't need to run it more than once as its content is pretty much static.
    """
    pages = []
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    cities = geocoding.load_coordinates_for_cities()
    cities = [city for city in cities if city[2][-2:] == "00"]
    top_cities = [(slugify(l[1].lower()), l[2]) for l in sorted(cities, key=operator.itemgetter(3), reverse=True)[:94]]

    rome_descriptions = settings.ROME_DESCRIPTIONS.values()

    for rome in rome_descriptions:
        occupation = slugify(rome)
        for city, zipcode in top_cities:
            url = "https://labonneboite.pole-emploi.fr/entreprises/%s-%s/%s" % (city, zipcode, occupation)
            pages.append((url, now_str))

    # a sitemap should have at most 50K URLs
    # see https://en.wikipedia.org/wiki/Sitemaps#Sitemap_limits
    if len(pages) >= 50000:
        raise Exception("sitemap should have at most 50K URLs")

    sitemap_xml = render_template('sitemap.xml', pages=pages)
    sitemap_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../web/static/sitemap.xml")
    with open(sitemap_filename, "w") as f:
        f.write(sitemap_xml)

    print "generated sitemap.xml using %s pages (%s cities x %s rome_descriptions)" % (
        len(pages),
        len(top_cities),
        len(rome_descriptions)
    )

if __name__ == "__main__":
    manager.run()
