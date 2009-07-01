"""
Screen scraper for NYC SCOUT data.

http://gis.nyc.gov/moo/scout/

To check status of a particular service request by service request ID:
http://www.nyc.gov/portal/site/threeoneone/

There's no way to get a permalink for a particular service request, because
they have a CAPTCHA. But at least this URL prepopulates the search field with
the given service request ID ("XXX"):
http://www.nyc.gov/portal/site/threeoneone/template.PAGE/menuitem.dfb4f4b32cf05387fd8a9010acd2f9a0/?servicerequestnumber=XXX
"""

from django.contrib.gis.geos import Point
from django.utils import simplejson
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from lxml import etree
import re

def parse_json(value):
    # This is custom for the JSON returned by the SCOUT site, which has some
    # funky stuff.
    value = re.sub(r'^\{\}\&\&', '', value)  # Trim leading "{}&&"
    value = re.sub(r'^\/\*', '', value)      # Trim leading "/*"
    value = re.sub(r'\*\/$', '', value)      # Trim trailing "*/"
    return simplejson.loads(value)

class ScoutScraper(NewsItemListDetailScraper):
    schema_slugs = ('scout',)
    has_detail = False
    sleep = 3

    def list_pages(self):
        # In my tests, I found that it's possible to get *every* point in NYC
        # with this two step process:
        #     1. Search for a Community Board.
        #     2. Zoom out one level.
        # Originally, this script searched each Community Board, but due to the
        # way the SCOUT site works, that meant that there was much duplication
        # in the data -- when you do a search for a CB, the site returns all
        # points within a pretty broad bounding box around that CB (i.e., not
        # just the points within the CB itself).

        # First, do a search for Community Board 405 (Queens #5). This is
        # located centrally in the city, just to be safe.
        data = {
            'clientQuery': '',
            'mapData': {
                "applicationName":"SCOUT",
                "cacheName":"basic",
                "clientDataStore":{
                    "declaredClass":"CDS",
                    "thematicPolygon":True,
                    "themeAlias":"C0",
                    "themeCountAlias":"C1",
                    "themeFeatureTypeName":"COMMUNITY_BOARD"
                },
                "declaredClass":"MD",
                "groupedClientData":{
                    "declaredClass":"PGD",
                    "envelope":{
                        "declaredClass":"ME",
                        "height":152878.5,
                        "maxX":1067317.2,
                        "maxY":272931.8,
                        "minX":913090.8,
                        "minY":120053.3,
                        "width":154226.4
                    },
                    "polygonGroupedClientData":True,
                    "themeFeatureTypeName":"COMMUNITY_BOARD"
                },
                "legend":{
                    "declaredClass":"LEG",
                    "description":"Days Since Last SCOUT Inspection by Community Board",
                    "markup":"""<?xml version="1.0" encoding="UTF-8"?><xhtml:div xmlns:svg="http://www.w3.org/2000/svg" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink"><svg:svg height="57px" version="1.1" width="186px"><svg:rect fill="#C9BFAB" fill-opacity="1.0" height="14" id="bucket0bg" title="1 to 10 days" width="14" x="5.0" y="5.0"/><svg:rect fill="#F03B20" fill-opacity="0.8" height="14" id="bucket0rect" title="1 to 10 days" width="14" x="5.0" y="5.0"/><svg:rect fill="#C9BFAB" fill-opacity="1.0" height="14" id="bucket1bg" title="11 to 20 days" width="14" x="5.0" y="23.0"/><svg:rect fill="#FEB24C" fill-opacity="0.8" height="14" id="bucket1rect" title="11 to 20 days" width="14" x="5.0" y="23.0"/><svg:rect fill="#C9BFAB" fill-opacity="1.0" height="14" id="bucket2bg" title="21 or more days" width="14" x="5.0" y="41.0"/><svg:rect fill="#FFEDA0" fill-opacity="0.8" height="14" id="bucket2rect" title="21 or more days" width="14" x="5.0" y="41.0"/></svg:svg><xhtml:div class="polyLeg"><xhtml:div id="polyLegBucket0" title="1 to 10 days">1 to 10 days</xhtml:div><xhtml:div id="polyLegBucket1" title="11 to 20 days">11 to 20 days</xhtml:div><xhtml:div id="polyLegBucket2" title="21 or more days">21 or more days</xhtml:div></xhtml:div></xhtml:div>"""
                },
                "markupType":"svg",
                "searches":[
                    {
                        "request":{
                            "declaredClass":"ARE",
                            "featureName":"405",
                            "featureTypeName":"COMMUNITY_BOARD",
                            "searchType":"AreaSearch"
                        },
                        "searchType":"AreaSearch",
                        "declaredClass":"SEA",
                        "visible":True,
                        "id":"",
                        "title":""
                    }
                ],
                "tileCacheDescription":{
                    "declaredClass":"MID",
                    "height":2560,
                    "mapEnvelope":{
                        "declaredClass":"ME",
                        "height":777777.8,
                        "maxX":1322222.2,
                        "maxY":595555.6,
                        "minX":700000,
                        "minY":-182222.2,
                        "width":622222.2
                    },
                    "width":2048
                },
                "viewportDescription":{
                    "declaredClass":"ID",
                    "height":678,
                    "mapEnvelope":{
                        "declaredClass":"ME",
                        "height":205989.6,
                        "maxX":1104136.3,
                        "maxY":299487.3,
                        "minX":876271.7,
                        "minY":93497.7,
                        "width":227864.6
                    },
                    "offset":{
                        "declaredClass":"IP",
                        "x":-580,
                        "y":-974
                    },
                    "width":750
                },
                "visibleCompoundFeatureTypeNames":[],
                "zoomLevel":1,
                "applicationChanged":True,
                "cumulativeMapDrag":{
                    "declaredClass":"IP",
                    "y":0,
                    "x":0
                }
            },
            'themeName': 'COMMUNITY_BOARD',
        }
        data = dict([(k, simplejson.dumps(v)) for k, v in data.items()])
        data.update({'methodName': 'find'}) # This doesn't get JSON-escaped.

        # We don't actually do anything with the result. We just needed the
        # server to set a cookie.
        html = self.get_html('http://gis.nyc.gov/doitt/webmap/ClientQueryMapper', data)

        # Next, zoom the map out one level. As a result, the map will display
        # *every* SCOUT point in the city.
        data = {
            'clientQuery': '',
            'mapData': {
                "applicationName":"SCOUT",
                "cacheName":"basic",
                "declaredClass":"MD",
                "groupedClientData":{
                    "declaredClass":"POI",
                    "envelope":{
                        "declaredClass":"ME",
                        "height":148573,
                        "maxX":1067096,
                        "maxY":270929,
                        "minX":913357,
                        "minY":122356,
                        "width":153739
                    }
                },
                "legend":{
                    "declaredClass":"LEG",
                    "description":"Service Request Count by Location",
                    "markup":"""<?xml version="1.0" encoding="UTF-8"?><xhtml:div xmlns:svg="http://www.w3.org/2000/svg" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink"><svg:svg height="120px" version="1.1" width="227px"><svg:circle cx="22.0" cy="10.0" fill="#FF9900" fill-opacity="1.0" id="bucket0" r="5" stroke="#000000" stroke-width="1" title="1 Request"/><svg:circle cx="22.0" cy="30.0" fill="#FF9900" fill-opacity="1.0" id="bucket1" r="10" stroke="#000000" stroke-width="1" title="2 to 3 Requests"/><svg:circle cx="22.0" cy="60.0" fill="#FF9900" fill-opacity="1.0" id="bucket2" r="15" stroke="#000000" stroke-width="1" title="4 Requests"/><svg:circle cx="22.0" cy="100.0" fill="#FF9900" fill-opacity="1.0" id="bucket3" r="20" stroke="#000000" stroke-width="1" title="5 Requests"/></svg:svg><xhtml:div class="ptLeg"><xhtml:div id="ptLegBucket0" title="1 Request">1 Request</xhtml:div><xhtml:div id="ptLegBucket1" title="2 to 3 Requests">2 to 3 Requests</xhtml:div><xhtml:div id="ptLegBucket2" title="4 Requests">4 Requests</xhtml:div><xhtml:div id="ptLegBucket3" title="5 Requests">5 Requests</xhtml:div></xhtml:div></xhtml:div>"""
                },
                "markupType":"svg",
                "searches":[{
                    "declaredClass":"SEA",
                    "id":"searched_COMMUNITY_BOARD.405",
                    "mapPoints":[[
                        {"declaredClass":"MP","x":1020138.6,"y":193489.6},
                        {"declaredClass":"MP","x":1020380.4,"y":193638.6},
                        {"declaredClass":"MP","x":1020499.7,"y":193766.7},
                        {"declaredClass":"MP","x":1020611.1,"y":193976.4},
                        {"declaredClass":"MP","x":1020752.8,"y":194634.2},
                        {"declaredClass":"MP","x":1020891.5,"y":194894.2},
                        {"declaredClass":"MP","x":1021126.3,"y":195114.5},
                        {"declaredClass":"MP","x":1021435.3,"y":195266.6},
                        {"declaredClass":"MP","x":1021969.7,"y":195365},
                        {"declaredClass":"MP","x":1022400.2,"y":195335.8},
                        {"declaredClass":"MP","x":1022932.7,"y":195221.9},
                        {"declaredClass":"MP","x":1023080.5,"y":195222.2},
                        {"declaredClass":"MP","x":1023301.2,"y":195265.5},
                        {"declaredClass":"MP","x":1023567,"y":195397.5},
                        {"declaredClass":"MP","x":1023364.6,"y":194817.6},
                        {"declaredClass":"MP","x":1023830.1,"y":194779},
                        {"declaredClass":"MP","x":1023853.9,"y":194947.3},
                        {"declaredClass":"MP","x":1024372.5,"y":195063.6},
                        {"declaredClass":"MP","x":1024373,"y":195283.9},
                        {"declaredClass":"MP","x":1024363,"y":195503.9},
                        {"declaredClass":"MP","x":1024287.4,"y":195696.6},
                        {"declaredClass":"MP","x":1023344.9,"y":196583.5},
                        {"declaredClass":"MP","x":1023253.1,"y":196811.6},
                        {"declaredClass":"MP","x":1023131,"y":197920.6},
                        {"declaredClass":"MP","x":1023164.4,"y":198133.2},
                        {"declaredClass":"MP","x":1023124.4,"y":198574.8},
                        {"declaredClass":"MP","x":1023185.6,"y":199216.4},
                        {"declaredClass":"MP","x":1023166,"y":199548.9},
                        {"declaredClass":"MP","x":1023050.1,"y":199776.4},
                        {"declaredClass":"MP","x":1022222.2,"y":200786.3},
                        {"declaredClass":"MP","x":1021605.5,"y":201612},
                        {"declaredClass":"MP","x":1020479.3,"y":203234.9},
                        {"declaredClass":"MP","x":1020106.7,"y":204189.9},
                        {"declaredClass":"MP","x":1019884.6,"y":204987.2},
                        {"declaredClass":"MP","x":1018857.7,"y":205510.4},
                        {"declaredClass":"MP","x":1018092.5,"y":205155.1},
                        {"declaredClass":"MP","x":1017866,"y":204937},
                        {"declaredClass":"MP","x":1017666.8,"y":204832.5},
                        {"declaredClass":"MP","x":1016544.3,"y":204742},
                        {"declaredClass":"MP","x":1015968.8,"y":204629.6},
                        {"declaredClass":"MP","x":1015765.4,"y":205474.7},
                        {"declaredClass":"MP","x":1015372.1,"y":206818.4},
                        {"declaredClass":"MP","x":1015144.5,"y":206905.5},
                        {"declaredClass":"MP","x":1014983.6,"y":206927.6},
                        {"declaredClass":"MP","x":1013963.5,"y":206891.2},
                        {"declaredClass":"MP","x":1013707.1,"y":206949.7},
                        {"declaredClass":"MP","x":1013370.2,"y":207076.9},
                        {"declaredClass":"MP","x":1012432.4,"y":207143.8},
                        {"declaredClass":"MP","x":1012177,"y":207113.4},
                        {"declaredClass":"MP","x":1011921.1,"y":206998.3},
                        {"declaredClass":"MP","x":1011789.4,"y":206876.7},
                        {"declaredClass":"MP","x":1010530.2,"y":204869.1},
                        {"declaredClass":"MP","x":1010047.4,"y":204367.3},
                        {"declaredClass":"MP","x":1008483.7,"y":202784.1},
                        {"declaredClass":"MP","x":1008446,"y":202800.4},
                        {"declaredClass":"MP","x":1007469.6,"y":202399.7},
                        {"declaredClass":"MP","x":1007380.1,"y":202333.4},
                        {"declaredClass":"MP","x":1006406.3,"y":202601.2},
                        {"declaredClass":"MP","x":1006280.6,"y":202687.2},
                        {"declaredClass":"MP","x":1006382.3,"y":203060.5},
                        {"declaredClass":"MP","x":1005805,"y":203433.2},
                        {"declaredClass":"MP","x":1004612.1,"y":203081.3},
                        {"declaredClass":"MP","x":1004944,"y":202197.3},
                        {"declaredClass":"MP","x":1005267.1,"y":201608.1},
                        {"declaredClass":"MP","x":1005240.4,"y":201067.4},
                        {"declaredClass":"MP","x":1005583.3,"y":200504.6},
                        {"declaredClass":"MP","x":1005218.3,"y":199986.9},
                        {"declaredClass":"MP","x":1005307.8,"y":199417.9},
                        {"declaredClass":"MP","x":1005809.1,"y":198997.9},
                        {"declaredClass":"MP","x":1005960.9,"y":198648.3},
                        {"declaredClass":"MP","x":1006000.2,"y":198338.2},
                        {"declaredClass":"MP","x":1006222.4,"y":198151.3},
                        {"declaredClass":"MP","x":1005904.8,"y":197738},
                        {"declaredClass":"MP","x":1008702.9,"y":195568.9},
                        {"declaredClass":"MP","x":1008399.2,"y":195177.6},
                        {"declaredClass":"MP","x":1009016.7,"y":194698.8},
                        {"declaredClass":"MP","x":1008703.9,"y":194294.8},
                        {"declaredClass":"MP","x":1010798.5,"y":192753.1},
                        {"declaredClass":"MP","x":1010373.3,"y":192179.5},
                        {"declaredClass":"MP","x":1011406.6,"y":191405.4},
                        {"declaredClass":"MP","x":1011508.6,"y":191282},
                        {"declaredClass":"MP","x":1011637.5,"y":191201.3},
                        {"declaredClass":"MP","x":1011455,"y":191069.6},
                        {"declaredClass":"MP","x":1011865.2,"y":190015.8},
                        {"declaredClass":"MP","x":1011661,"y":189904.1},
                        {"declaredClass":"MP","x":1012956.9,"y":187926.9},
                        {"declaredClass":"MP","x":1013388.4,"y":188598.9},
                        {"declaredClass":"MP","x":1013639.1,"y":188908.6},
                        {"declaredClass":"MP","x":1014058.7,"y":188284.5},
                        {"declaredClass":"MP","x":1014297.8,"y":188510.5},
                        {"declaredClass":"MP","x":1014735.2,"y":188754.5},
                        {"declaredClass":"MP","x":1014861.1,"y":188581},
                        {"declaredClass":"MP","x":1015289.2,"y":188967},
                        {"declaredClass":"MP","x":1015415.9,"y":189225.3},
                        {"declaredClass":"MP","x":1015959.2,"y":189541.9},
                        {"declaredClass":"MP","x":1016482.3,"y":189904.8},
                        {"declaredClass":"MP","x":1017665,"y":191102.6},
                        {"declaredClass":"MP","x":1019184.7,"y":192213.9},
                        {"declaredClass":"MP","x":1020599.4,"y":192565.5},
                        {"declaredClass":"MP","x":1020138.6,"y":193489.6}
                    ]],
                    "request":{
                        "declaredClass":"ARE",
                        "featureName":"405",
                        "featureTypeName":"COMMUNITY_BOARD"
                    },
                    "searchType":"AreaSearch",
                    "title":"Community Board: 5 QUEENS",
                    "visible":True
                }],
                "tileCacheDescription":{
                    "declaredClass":"MID",
                    "height":2560,
                    "mapEnvelope":{
                        "declaredClass":"ME",
                        "height":142222.2,
                        "maxX":1069777.8,
                        "maxY":269333.3,
                        "minX":956000,
                        "minY":127111.1,
                        "width":113777.8
                    },
                    "width":2048
                },
                "viewportDescription":{
                    "declaredClass":"ID",
                    "height":678,
                    "mapEnvelope":{
                        "declaredClass":"ME",
                        "height":37666.7,
                        "maxX":1035325.9,
                        "maxY":216368.7,
                        "minX":993659.2,
                        "minY":178702,
                        "width":41666.7
                    },
                    "offset":{
                        "declaredClass":"IP",
                        "x":-678,
                        "y":-953
                    },
                    "width":750
                },
                "visibleCompoundFeatureTypeNames":[],
                "zoomLevel":4,
                "cumulativeMapDrag":{
                    "declaredClass":"IP",
                    "y":0,
                    "x":0
                }
            },
            'themeName': 'COMMUNITY_BOARD',
        }
        data = dict([(k, simplejson.dumps(v)) for k, v in data.items()])
        data.update({'methodName': 'zoomToLevel', 'zoomLevel': '3'}) # This doesn't get JSON-escaped.
        html = self.get_html('http://gis.nyc.gov/doitt/webmap/ClientQueryMapper', data)

        # The result is a JSON string whose 'markup' value is XML that contains
        # a <circle> for every circle on the map. A circle has one or more
        # actual items on it, and the only way to get the detail record is by
        # doing another query for each circle.
        data = parse_json(html)
        xml_string = data['markup'].replace('<\\/', '</').encode('utf8')
        xml = etree.fromstring(xml_string)
        circle_list = etree.ETXPath('//{http://www.w3.org/2000/svg}circle')(xml)
        num_circles = len(circle_list)
        self.logger.debug('Found %s circles', num_circles)

        for i, circle in enumerate(circle_list):
            x, y = circle.attrib['id'].split('@')
            seconds_remaining = self.sleep * (num_circles - i - 1)
            self.logger.debug('Getting circle %s of %s. Time remaining: %s minutes', i, num_circles, (seconds_remaining // 60))
            data = {
                'applicationName': 'SCOUT',
                'caller': '_idClientData',
                'callerWindow': '',
                'clientQuery': '',
                'cumulativeMapDrag': {
                    "preamble": None,
                    "declaredClass": "gov.nyc.doitt.gis.geometry.domain.ImagePoint",
                    "y": 0,
                    "x": 0,
                },
                'featureId': '"%s"' % circle.attrib['id'],
                'featureTypeName': 'locations',
                'mapData': {
                    u'applicationChanged': False,
                    u'applicationName': u'SCOUT',
                    u'cacheName': u'basic',
                    u'clientDataStore': {
                        u'declaredClass': u'gov.nyc.doitt.gis.webmap.domain.ClientDataStore',
                        u'identifier': u'C0',
                        u'thematicPolygon': False,
                        u'xCoordAlias': u'C1',
                        u'yCoordAlias': u'C2'
                    },
                    u'cumulativeMapDrag': {
                        u'declaredClass': u'gov.nyc.doitt.gis.geometry.domain.ImagePoint',
                        u'preamble': None,
                        u'x': 0,
                        u'y': 0
                    },
                    u'declaredClass': u'gov.nyc.doitt.gis.service.webmap.domain.MapData',
                    u'filterField': u'',
                    u'filterValue': u'',
                    u'groupedClientData': {
                        u'declaredClass': u'gov.nyc.doitt.gis.service.webmap.domain.PointGroupedClientData',
                        u'envelope': {
                            u'declaredClass': u'gov.nyc.doitt.gis.geometry.domain.MapEnvelope',
                            u'height': 146449,
                            u'maxX': 1066580,
                            u'maxY': 270798,
                            u'minX': 915309,
                            u'minY': 124349,
                            u'width': 151271
                        }
                    },
                    u'legend': {
                        u'declaredClass': u'gov.nyc.doitt.gis.service.webmap.domain.Legend',
                        u'description': u'Service Request Count by Location',
                        u'markup': u'<?xml version="1.0" encoding="UTF-8"?><xhtml:div xmlns:xhtml="http://www.w3.org/1999/xhtml"><svg:svg xmlns:svg="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" height="120px" version="1.1" width="172px"><svg:circle cx="22.0" cy="10.0" fill="#FF9900" fill-opacity="1.0" id="bucket0" r="5" stroke="#000000" stroke-width="1" title="1 Request" xmlns:svg="http://www.w3.org/2000/svg"/><svg:circle cx="22.0" cy="30.0" fill="#FF9900" fill-opacity="1.0" id="bucket1" r="10" stroke="#000000" stroke-width="1" title="2 Requests" xmlns:svg="http://www.w3.org/2000/svg"/><svg:circle cx="22.0" cy="60.0" fill="#FF9900" fill-opacity="1.0" id="bucket2" r="15" stroke="#000000" stroke-width="1" title="3 Requests" xmlns:svg="http://www.w3.org/2000/svg"/><svg:circle cx="22.0" cy="100.0" fill="#FF9900" fill-opacity="1.0" id="bucket3" r="20" stroke="#000000" stroke-width="1" title="4 Requests" xmlns:svg="http://www.w3.org/2000/svg"/></svg:svg><xhtml:div class="ptLeg" xmlns:xhtml="http://www.w3.org/1999/xhtml"><xhtml:div id="ptLegBucket0" title="1 Request">1 Request</xhtml:div><xhtml:div id="ptLegBucket1" title="2 Requests">2 Requests</xhtml:div><xhtml:div id="ptLegBucket2" title="3 Requests">3 Requests</xhtml:div><xhtml:div id="ptLegBucket3" title="4 Requests">4 Requests</xhtml:div></xhtml:div></xhtml:div>'
                    },
                    u'markup': None,
                    u'markupType': u'svg',
                    u'pointThemeDisabled': False,
                    u'responseStatus': {
                        u'code': 0,
                        u'declaredClass': u'gov.nyc.doitt.gis.service.webmap.domain.ResponseStatus'
                    },
                    u'searches': [
                        {
                            u'declaredClass': u'gov.nyc.doitt.gis.service.webmap.domain.Search',
                            u'found': False,
                            u'id': u'searched_COMMUNITY_BOARD.405',
                            u'mapPoints': [],
                            u'request': {
                                u'declaredClass': u'gov.nyc.doitt.gis.service.webmap.domain.AreaRequest',
                                u'featureName': u'405',
                                u'featureTypeName': u'COMMUNITY_BOARD'
                            },
                            u'searchType': u'AreaSearch',
                            u'title': u'Community Board: 5 QUEENS',
                            u'visible': True
                        }
                    ],
                    u'tableOfContents': {
                        u'declaredClass': u'gov.nyc.doitt.gis.webmap.domain.TableOfContents',
                        u'featureTypeGroups': [],
                        u'name': u'SCOUT',
                        u'title': u'Scout Table of Contents'
                    },
                    u'viewportDescription': {
                        u'declaredClass': u'gov.nyc.doitt.gis.service.webmap.domain.ImageDescription',
                        u'height': 678,
                        u'mapEnvelope': {
                            u'declaredClass': u'gov.nyc.doitt.gis.geometry.domain.MapEnvelope',
                            u'height': 75333.333333333256,
                            u'maxX': 1056159.1666666665,
                            u'maxY': 235202.16666666663,
                            u'minX': 972825.83333333337,
                            u'minY': 159868.83333333337,
                            u'width': 83333.333333333139
                        },
                        u'offset': {
                            u'declaredClass': u'gov.nyc.doitt.gis.geometry.domain.ImagePoint',
                            u'x': -919,
                            u'y': -819
                        },
                        u'width': 750
                    },
                    u'zoomLevel': 3
                },
                'point': {
                    "x": 311,
                    "y": 435,
                    "preamble": None,
                    "declaredClass": "gov.nyc.doitt.gis.geometry.domain.ImagePoint"
                },
                'themeName': '"COMMUNITY_BOARD"',
            }
            data.update({'methodName': 'identify', 'x': x.split('.')[0], 'y': y.split('.')[0]}) # This doesn't get JSON-escaped.
            yield self.get_html('http://gis.nyc.gov/doitt/webmap/Identify', data)

    def parse_list(self, html):
        detail_data = parse_json(html)
        aliases = (
            ('C0', 'identifier'),
            ('C1', 'x_coord'),
            ('C2', 'y_coord'),
            ('C3', 'complaint_type'),
            ('C4', 'created_time'),
            ('C5', 'created_date'),
            ('C6', 'status'),
            ('C7', 'community_board'),
            ('C8', 'agency_name'),
            ('C9', 'agency_abbr'),
            ('C10', 'description'),
            ('C11', 'sr_id'),
        )
        for item in detail_data['data']['items']:
            for k, v in aliases:
                item[v] = item.pop(k)
            yield item

    def clean_list_record(self, record):
        created_datetime = parse_date(record['created_time'], '%m/%d/%Y %H:%M', return_datetime=True)
        record['created_date'] = created_datetime.date()
        record['created_time'] = created_datetime.time()

        record['x_coord'] = float(record['x_coord'])
        record['y_coord'] = float(record['y_coord'])

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['sr_id'], record['sr_id'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        agency = self.get_or_create_lookup('agency', list_record['agency_name'], list_record['agency_name'])
        complaint_type = self.get_or_create_lookup('complaint_type', list_record['complaint_type'], list_record['complaint_type'])
        description = self.get_or_create_lookup('description', list_record['description'], list_record['description'])
        status = self.get_or_create_lookup('status', list_record['status'], list_record['status'])
        title = '%s: %s' % (complaint_type.name, description.name)
        location_name = 'See map for location'
        new_attributes = {
            'agency': agency.id,
            'complaint_type': complaint_type.id,
            'description': description.id,
            'status': status.id,
            'created_time': list_record['created_time'],
            'sr_id': list_record['sr_id'],
            'x_coord': list_record['x_coord'],
            'y_coord': list_record['y_coord'],
        }
        if old_record is None:
            self.create_newsitem(
                new_attributes,
                title=title,
                item_date=list_record['created_date'],
                location=Point(list_record['x_coord'], list_record['y_coord'], srid=2263),
                location_name=location_name,
            )
        else:
            new_values = {'title': title, 'item_date': list_record['created_date'], 'location_name': location_name}
            self.update_existing(old_record, new_values, new_attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    ScoutScraper().update()
