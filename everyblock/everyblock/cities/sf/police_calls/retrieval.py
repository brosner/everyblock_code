"""
Importer for SF crime.
http://www.sfgov.org/site/uploadedfiles/police/ftpfiles/CADdataZIP.tar.gz
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date, parse_time
from ebpub.utils.text import clean_address
from cStringIO import StringIO
from lxml import etree
import re
import tarfile

item_xpath = etree.XPath('//CRIME_ID')

# This maps the SFPD's categories to tuples of (broad_category, detail_category).
CUSTOM_CATEGORIES = {
    'ABANDONED VEH': ('Police action/assistance', 'Police action/assistance'),
    'AGGR ASSAULT/ADW': ('Violent crime', 'Assault'),
    'AGGR ASSAULT/ADW - DV': ('Domestic violence', 'Assault'),
    'AIDED CASE': ('Police action/assistance', 'Police action/assistance'),
    'ALARM': ('Nonviolent crime', 'Alarm'),
    'AMBULANCE': ('Police action/assistance', 'Police action/assistance'),
    'ARREST MADE': ('Police action/assistance', 'Police action/assistance'),
    'ASSAULT/BATTERY': ('Violent crime', 'Assault'),
    'ASSAULT/BATTERY - DV': ('Domestic violence', 'Assault'),
    'ATTEMPT SUICIDE': ('Disorder', 'Attempted suicide'),
    'AUTO BOOST/STRIP': ('Nonviolent crime', 'Theft'),
    'BOMB THREAT': ('Violent crime', 'Disorder'),
    'BONFIRE': ('Disorder', 'Disorder'),
    'BRGLR ALRM AUDIB': ('Nonviolent crime', 'Alarm'),
    'BRGLR ALRM SILNT': ('Nonviolent crime', 'Alarm'),
    'BRGLR ALRM VEHIC': ('Nonviolent crime', 'Alarm'),
    'BROKEN WINDOW': ('Nonviolent crime', 'Vandalism'),
    'BURGLARY': ('Nonviolent crime', 'Theft'),
    'CANCEL COMPLAINT': ('Other', 'Other'),
    'CHECK WELL BEING': ('Police action/assistance', 'Police action/assistance'),
    'CHECK WELL BEING - DV': ('Domestic violence', 'Police action/assistance'),
    'CIT REQ INTER -DV': ('Domestic violence', 'Police action/assistance'),
    'CITIZEN ARREST': ('Police action/assistance', 'Police action/assistance'),
    'CITIZEN STANDBY': ('Police action/assistance', 'Police action/assistance'),
    'CITIZEN STANDBY - DV': ('Domestic violence', 'Police action/assistance'),
    'CITY LOT CHECK': ('Police action/assistance', 'Police action/assistance'),
    'COMPLAINT UNKN': ('Other', 'Other'),
    'CORONER': ('Police action/assistance', 'Police action/assistance'),
    'DEMONSTRATION': ('Disorder', 'Disorder'),
    'DRIVEWAY - TOW': ('Police action/assistance', 'Police action/assistance'),
    'DRUNK DRIVER': ('Nonviolent crime', 'Nonviolent crime'),
    'EXPLOSION': ('Disorder', 'Disorder'),
    'FIGHT W/WEAPON': ('Violent crime', 'Fight'),
    'FIGHT W/WEAPONS DV': ('Domestic violence', 'Fight'),
    'FIGHT-NO WEAPONS': ('Violent crime', 'Fight'),
    'FIGHT-NO WEAPONS - DV': ('Domestic violence', 'Fight'),
    'FIRE': ('Disorder', 'Disorder'),
    'FRAUD': ('Nonviolent crime', 'Nonviolent crime'),
    'GRAFFITI': ('Nonviolent crime', 'Vandalism'),
    'GRAND THEFT': ('Nonviolent crime', 'Theft'),
    'HAZMAT INCIDENT': ('Police action/assistance', 'Police action/assistance'),
    'HOMICIDE': ('Violent crime', 'Homicide'),
    'IN SVC/ON FOOT': ('Police action/assistance', 'Police action/assistance'),
    'IND EXPOSURE': ('Nonviolent crime', 'Nonviolent crime'),
    'INTOX PERSON': ('Disorder', 'Disorder'),
    'JUV BEYOND CONT': ('Police action/assistance', 'Police action/assistance'),
    'JUVENILE DIST': ('Disorder', 'Disorder'),
    'KIDNAPPING': ('Violent crime', 'Kidnapping'),
    'MEET W/CITIZEN': ('Police action/assistance', 'Police action/assistance'),
    'MEET W/OFFICER': ('Police action/assistance', 'Police action/assistance'),
    'MENT DISTURBED': ('Disorder', 'Disorder'),
    'MISSING JUV': ('Police action/assistance', 'Police action/assistance'),
    'MISSING PERSON': ('Police action/assistance', 'Police action/assistance'),
    'MUNI ALARM': ('Nonviolent crime', 'Alarm'),
    'MUNI INSP PROG': ('Police action/assistance', 'Police action/assistance'),
    'NOISE NUISANCE': ('Disorder', 'Threats'),
    'PANIC ALARM': ('Nonviolent crime', 'Alarm'),
    'PARKING': ('Nonviolent crime', 'Nonviolent crime'),
    'PASSING CALL': ('Police action/assistance', 'Police action/assistance'),
    'PER.BREAKING IN': ('Nonviolent crime', 'Person breaking in'),
    'PER.BREAKING IN.DV': ('Nonviolent crime', 'Person breaking in'),
    'PERS RING DOOR': ('Disorder', 'Disorder'),
    'PERSON DOWN': ('Disorder', 'Disorder'),
    'PERSON DUMPING': ('Nonviolent crime', 'Nonviolent crime'),
    'PERSON SCREAMING': ('Disorder', 'Disorder'),
    'PERSON W/KNIFE': ('Violent crime', 'Person with knife'),
    'PERSON W/KNIFE - DV': ('Domestic violence', 'Person with knife'),
    'PERSON WITH GUN': ('Violent crime', 'Gun-related'),
    'PETTY THEFT': ('Nonviolent crime', 'Theft'),
    'PRIS. TRANSPORT': ('Police action/assistance', 'Police action/assistance'),
    'PROWLER': ('Nonviolent crime', 'Nonviolent crime'),
    'PSYCH EVAL': ('Police action/assistance', 'Police action/assistance'),
    'PURSESNATCH': ('Nonviolent crime', 'Theft'),
    'Police label': ('Umbrella', 'Detail bucket'),
    'RECVR STOLEN VEH': ('Police action/assistance', 'Theft'),
    'RESISTING ARREST': ('Disorder', 'Disorder'),
    'RESPOND BACKUP': ('Police action/assistance', 'Police action/assistance'),
    'ROADBLOCK': ('Disorder', 'Disorder'),
    'ROBBERY': ('Violent crime', 'Theft'),
    'ROLL INTOX PERS': ('Nonviolent crime', 'Theft'),
    'SENILE PERSON': ('Disorder', 'Disorder'),
    'SERVICE REQUEST': ('Police action/assistance', 'Police action/assistance'),
    'SEX CRIME.CHILD': ('Violent crime', 'Sexual assault'),
    'SEXUAL ASSAULT': ('Violent crime', 'Sexual assault'),
    'SEXUAL ASSAULT - DV': ('Domestic violence', 'Sexual assault'),
    'SHOOTING': ('Violent crime', 'Gun-related'),
    'SHOTS FIRED': ('Violent crime', 'Gun-related'),
    'SHOTSPOTTER': ('Violent crime', 'Gun-related'),
    'SILNT HLDUP ALARM': ('Nonviolent crime', 'Alarm'),
    'SOLICITING PROS': ('Nonviolent crime', 'Nonviolent crime'),
    'STABBING/CUTTING': ('Violent crime', 'Stabbing/cutting'),
    'STABBING/CUTTING - DV': ('Domestic violence', 'Stabbing/cutting'),
    'STOLEN PROPERTY': ('Nonviolent crime', 'Theft'),
    'STOLEN VEHICLE': ('Nonviolent crime', 'Theft'),
    'STRONGARM ROB.': ('Violent crime', 'Strong-arm robbery'),
    'SUSP HOMELESS': ('Disorder', 'Disorder'),
    'SUSP PERSON': ('Disorder', 'Disorder'),
    'SUSP PERSON-VEH': ('Disorder', 'Disorder'),
    'SUSPIC. MAILING': ('Nonviolent crime', 'Nonviolent crime'),
    'THREATS': ('Violent crime', 'Threats'),
    'THREATS - DV': ('Domestic violence', 'Threats'),
    'TOW TRUCK': ('Police action/assistance', 'Police action/assistance'),
    'TRAFFIC STOP': ('Police action/assistance', 'Police action/assistance'),
    'TRESPASSER': ('Nonviolent crime', 'Nonviolent crime'),
    'VANDALISM': ('Nonviolent crime', 'Vandalism'),
    'VANDALISM - DV': ('Domestic violence', 'Vandalism'),
    'VEH ACC.INJ HR': ('Traffic incident', 'Vehicle accident'),
    'VEH ACCIDENT, HR': ('Traffic incident', 'Vehicle accident'),
    'VEH ACCIDENT, INJ': ('Traffic incident', 'Vehicle accident'),
    'VEH ACCIDENT, NI': ('Traffic incident', 'Vehicle accident'),
    'WANTED SUSP/VEH': ('Police action/assistance', 'Police action/assistance'),
    'YGC/JAIL ESCAPE': ('Police action/assistance', 'Police action/assistance')
}

class CrimeScraper(NewsItemListDetailScraper):
    schema_slugs = ('police-calls',)
    has_detail = False

    def list_pages(self):
        raw_file = self.get_html('http://www.sfgov.org/site/uploadedfiles/police/ftpfiles/CADdataZIP.tar.gz')
        tf = tarfile.open('', 'r:gz', StringIO(raw_file))
        for filename in tf.getnames():
            inner_file = tf.extractfile(filename)
            yield inner_file.read()

    def parse_list(self, text):
        if not text.startswith('<Root>'):
            # Older versions of the files are in text format, which isn't quite
            # valid XML, so we clean those up here.
            text = re.sub(r'\s*\d+ rows? selected\.\s*$', '', text)
            text = '<Root>%s</Root>' % text
        xml = etree.fromstring(text)
        for el in item_xpath(xml):
            data = dict([(t.tag, t.text) for t in el])
            data['crime_id'] = el.attrib['CRIME_ID']
            yield data

    def clean_list_record(self, record):
        record['CALL_DATE'] = parse_date(record['CALL_DATE'], '%Y-%m-%d')
        record['OFFENSE_DATE'] = parse_date(record['OFFENSE_DATE'], '%Y-%m-%d')
        record['REPORT_DATE'] = parse_date(record['REPORT_DATE'], '%Y-%m-%d')
        record['COMMON_LOCATION'] = record['COMMON_LOCATION'].strip()
        record['ADDRESS_NBR'] = record['ADDRESS_NBR'].strip()
        record['ADDRESS'] = record['ADDRESS'].strip()

        # The 'NARRATIVE' field includes time and disposition data. Parse that out.
        m = re.search(r'^Time: (?P<TIME>\d\d?:\d\d)<br>.*?<br>Disposition: (?P<DISPOSITION>.*)$', record.pop('NARRATIVE'))
        record.update(m.groupdict())

        record['TIME'] = parse_time(record['TIME'], '%H:%M')

        # Set location_name. The logic is different depending on the ADDRESS_TYPE.
        address_type = record['ADDRESS_TYPE']
        if address_type == 'PREMISE ADDRESS':
            record['location_name'] = '%s block of %s' % (record['ADDRESS_NBR'], clean_address(record['ADDRESS']))
        elif address_type == 'INTERSECTION':
            if '/' in record['ADDRESS']:
                streets = record['ADDRESS'].split('/')
                record['location_name'] = '%s and %s' % (clean_address(streets[0]), clean_address(streets[1]))
            else:
                record['location_name'] = clean_address(record['ADDRESS'])
        elif address_type == 'GEO-OVERRIDE':
            record['location_name'] = clean_address(record['ADDRESS'])
        elif address_type == 'COMMON LOCATION':
            if record['ADDRESS_NBR'] and record['ADDRESS']:
                record['location_name'] = '%s %s' % (record['ADDRESS_NBR'], clean_address(record['ADDRESS']))
            elif record['ADDRESS'] and record['COMMON_LOCATION']:
                record['location_name'] = '%s (%s)' % (clean_address(record['ADDRESS']), clean_address(record['COMMON_LOCATION']))
            elif record['COMMON_LOCATION']:
                record['location_name'] = clean_address(record['COMMON_LOCATION'])
            elif record['ADDRESS']:
                record['location_name'] = clean_address(record['ADDRESS'])
            else:
                record['location_name'] = 'Unknown'
        else:
            record['location_name'] = 'Unknown'

        try:
            d = CUSTOM_CATEGORIES[record['ORIG_CRIMETYPE_NAME']]
        except KeyError:
            d = ('Unknown', 'Unknown')
        record['broad_category'], record['detail_category'] = d

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['crime_id'], record['crime_id'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        result = self.get_or_create_lookup('result', list_record['DISPOSITION'], list_record['DISPOSITION'], make_text_slug=False)
        incident_type = self.get_or_create_lookup('incident_type', list_record['ORIG_CRIMETYPE_NAME'], list_record['ORIG_CRIMETYPE_NAME'], make_text_slug=False)
        broad_category = self.get_or_create_lookup('broad_category', list_record['broad_category'], list_record['broad_category'], make_text_slug=False)
        detail_category = self.get_or_create_lookup('detail_category', list_record['detail_category'], list_record['detail_category'], make_text_slug=False)
        address_type = self.get_or_create_lookup('address_type', list_record['ADDRESS_TYPE'], list_record['ADDRESS_TYPE'])
        values = {
            'title': incident_type.name,
            'item_date': list_record['OFFENSE_DATE'],
            'location_name': list_record['location_name'],
        }
        attributes = {
            'address_type': address_type.id,
            'crime_time': list_record['TIME'],
            'incident_type': incident_type.id,
            'broad_category': broad_category.id,
            'detail_category': detail_category.id,
            'result': result.id,
            'common_location': list_record['COMMON_LOCATION'],
            'call_date': list_record['CALL_DATE'],
            'report_date': list_record['REPORT_DATE'],
            'crime_id': list_record['crime_id'],
        }
        if old_record is None:
            self.create_newsitem(attributes, **values)
        else:
            self.update_existing(old_record, values, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    CrimeScraper().update()
