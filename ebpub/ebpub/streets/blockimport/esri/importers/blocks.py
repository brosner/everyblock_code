import re
import sys
from django.contrib.gis.gdal import DataSource
from ebpub.metros.models import Metro
from ebpub.streets.models import Block
from ebpub.streets.name_utils import make_pretty_name
from ebpub.utils.text import slugify

FIELD_MAP = {
    # ESRI        # Block
    'L_F_ADD'   : 'left_from_num',
    'L_T_ADD'   : 'left_to_num',
    'R_F_ADD'   : 'right_from_num',
    'R_T_ADD'   : 'right_to_num',
    'POSTAL_L'  : 'left_zip',
    'POSTAL_R'  : 'right_zip',
    'GEONAME_L' : 'left_city',
    'GEONAME_R' : 'right_city',
    'STATE_L'   : 'left_state',
    'STATE_R'   : 'right_state',
}

NAME_FIELD_MAP = {
    'NAME'      : 'street',
    'TYPE'      : 'suffix',
    'PREFIX'    : 'predir',
    'SUFFIX'    : 'postdir',
}

# FCC == feature classification code: indicates the type of road
VALID_FCC_PREFIXES = (
    'A1', # primary highway with limited access
    'A2', # primary road without limited access
    'A3', # secondary and connecting road
    'A4'  # local, neighborhood, and rural road
)

class EsriImporter(object):
    def __init__(self, shapefile, city=None, layer_id=0):
        ds = DataSource(shapefile)
        self.layer = ds[layer_id]
        self.city = city and city or Metro.objects.get_current().name
        self.fcc_pat = re.compile('^(' + '|'.join(VALID_FCC_PREFIXES) + ')\d$')

    def save(self, verbose=False):
        alt_names_suff = ('', '1', '2', '3', '4', '5')
        num_created = 0
        for i, feature in enumerate(self.layer):
            if not self.fcc_pat.search(feature.get('FCC')):
                continue
            parent_id = None
            fields = {}
            for esri_fieldname, block_fieldname in FIELD_MAP.items():
                value = feature.get(esri_fieldname)
                if isinstance(value, basestring):
                    value = value.upper()
                elif isinstance(value, int) and value == 0:
                    value = None
                fields[block_fieldname] = value
            if not ((fields['left_from_num'] and fields['left_to_num']) or
                    (fields['right_from_num'] and fields['right_to_num'])):
                continue
            # Sometimes the "from" number is greater than the "to"
            # number in the source data, so we swap them into proper
            # ordering
            for side in ('left', 'right'):
                from_key, to_key = '%s_from_num' % side, '%s_to_num' % side
                if fields[from_key] > fields[to_key]:
                    fields[from_key], fields[to_key] = fields[to_key], fields[from_key]
            if feature.geom.geom_name != 'LINESTRING':
                continue
            for suffix in alt_names_suff:
                name_fields = {}
                for esri_fieldname, block_fieldname in NAME_FIELD_MAP.items():
                    key = esri_fieldname + suffix
                    name_fields[block_fieldname] = feature.get(key).upper()
                if not name_fields['street']:
                    continue
                # Skip blocks with bare number street names and no suffix / type
                if not name_fields['suffix'] and re.search('^\d+$', name_fields['street']):
                    continue
                fields.update(name_fields)
                block = Block(**fields)
                block.geom = feature.geom.geos
                street_name, block_name = make_pretty_name(
                    fields['left_from_num'],
                    fields['left_to_num'],
                    fields['right_from_num'],
                    fields['right_to_num'],
                    fields['predir'],
                    fields['street'],
                    fields['suffix'],
                    fields['postdir']
                )
                block.pretty_name = block_name
                block.street_pretty_name = street_name
                block.street_slug = slugify(' '.join((fields['street'], fields['suffix'])))
                block.save()
                if parent_id is None:
                    parent_id = block.id
                else:
                    block.parent_id = parent_id
                    block.save()
                num_created += 1
                if verbose:
                    print >> sys.stderr, 'Created block %s' % block
        return num_created
