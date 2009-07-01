#!/usr/bin/env python
import sys
import logging
from ebpub.streets.models import make_pretty_name, Block
from ebpub.utils.text import slugify
from django.contrib.gis.gdal import DataSource

logger = logging.getLogger('eb.cities.miami.import_blocks')

def import_blocks(blocks_layer):
    sides = ('R', 'L')
    for i, feature in enumerate(blocks_layer):
        for side in sides:
            from_num = feature['%s_ADD_FROM' % side]
            to_num = feature['%s_ADD_TO' % side]
            zip = feature['%s_ZIP' % side]
            street_name = feature['ST_NAME']
            if from_num and to_num and zip and street_name:
                if from_num > to_num:
                    from_num, to_num = to_num, from_num
                street_pretty_name, block_pretty_name = make_pretty_name(
                    from_num, to_num, feature['PRE_DIR'], street_name,
                    feature['ST_TYPE'], feature['SUF_DIR'])
                block, created = Block.objects.get_or_create(
                    pretty_name=block_pretty_name,
                    predir=(feature['PRE_DIR'] or ''),
                    street=street_name,
                    street_slug=slugify('%s %s' % (street_name, (feature['ST_TYPE'] or ''))),
                    street_pretty_name=street_pretty_name,
                    suffix=(feature['ST_TYPE'] or ''),
                    postdir=(feature['SUF_DIR'] or ''),
                    from_num=from_num,
                    to_num=to_num,
                    zip=zip,
                    city='FAKE', # we don't know it yetc
                    state='FL',
                    location='SRID=4326;%s' % str(feature.geometry)
                )
                logger.debug('%s block %r' % (created and 'Created' or 'Already had', block))
                if i % 100 == 0:
                    logger.info('Created %s blocks' % i)

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        if len(argv) != 1:
            raise Usage('must provide path to streets shapefile')
        else:
            path = argv[0]
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)-15s %(levelname)-8s %(message)s')
        ds = DataSource(path)
        layer = ds[0]
        import_blocks(layer)
    except Usage, e:
        print >> sys.stderr, 'Usage: %s /path/to/shapefile' % sys.argv[0]
        print >> sys.stderr, e.msg
        return 2

if __name__ == '__main__':
    sys.exit(main())
