"""
Screen scraper for Charlotte calls for service (911 calls).
http://maps.cmpdweb.org/cfs/Default.aspx
"""

from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title, clean_address, address_to_block
from django.template.defaultfilters import capfirst
import re

SOURCE_URL = 'http://maps.cmpdweb.org/cfs/Default.aspx'

CATEGORIES = {
    '': 'UNKNOWN',
    '10-33 HELP ME QUICK': 'POLICE ACTION',
    '10-18 URGENT ASSISTANCE NEEDED': 'POLICE ACTION',
    'ABANDONED ANIMAL': 'ANIMAL RELATED',
    'ABANDONED PROPERTY': 'PROPERTY RELATED',
    'ABANDONED VEHICLE': 'PROPERTY RELATED',
    'A/C ASSIST OTHER AGENCY': 'POLICE ACTION',
    'A/C CHECK COMPLIANCE': 'POLICE ACTION',
    'ACCIDENT-FATALITY': 'TRAFFIC RELATED',
    'ACCIDENT IN ROADWAY-PROPERTY DAMAGE': 'TRAFFIC RELATED',
    'ACCIDENT NON ROADWAY-PROPERTY DAMAGE': 'TRAFFIC RELATED',
    'ACCIDENT-PERSONAL INJURY': 'TRAFFIC RELATED',
    'AGRRESSIVE ANIMAL': 'ANIMAL RELATED',
    'ALARM-AUDIBLE': 'ALARM',
    'ALARM-AUTO': 'ALARM',
    'ALARM-COMMERCIAL': 'ALARM',
    'ALARM-COMMERCIAL-HOLD UP': 'ALARM',
    'ALARM NO PERMIT NUMBER': 'ALARM',
    'ALARM PERSONAL': 'ALARM',
    'ALARM-RESIDENTIAL': 'ALARM',
    'ALARM-RESIDENTIAL-PRIORITY': 'ALARM',
    'ABC-INTOXICATED PERSON': 'ALCOHOL RELATED',
    'ABC-VIOLATIONS-CITATIONS': 'ALCOHOL RELATED',
    'ANIMAL ATTACK': 'ANIMAL RELATED',
    'ANIMAL BARKING': 'ANIMAL RELATED',
    'ANIMAL BITE': 'ANIMAL RELATED',
    'ANIMAL CRUELTY': 'ANIMAL RELATED',
    'ANIMAL EVICTION': 'ANIMAL RELATED',
    'ANIMAL FIGHTING': 'ANIMAL RELATED',
    'ANIMAL ODOR': 'ANIMAL RELATED',
    'ANIMAL RABIES EXPOSURE': 'ANIMAL RELATED',
    'ANIMAL SAFETY CONCERN REFERRAL': 'ANIMAL RELATED',
    'ANIMAL TRANSPORT': 'ANIMAL RELATED',
    'ANIMAL TRAP': 'ANIMAL RELATED',
    'ARMED PERSON': 'WEAPON RELATED',
    'ARMED TO THE TERROR OF PUBLIC': 'WEAPON RELATED',
    'ASSAULT- PHYSICAL ONLY': 'ASSAULT',
    'ADW- WITH INJURY': 'ASSAULT',
    'ADW-NO INJURY': 'ASSAULT',
    'ASSIST FIRE DEPARTMENT': 'POLICE ACTION',
    'ASSIST MEDIC': 'POLICE ACTION',
    'ASSIST OTHER AGENCY': 'POLICE ACTION',
    'ASSIST OTHER JURISDICTION': 'POLICE ACTION',
    'ASSIST WATER DEPARTMENT': 'POLICE ACTION',
    'ATTEMPT TO LOCATE': 'POLICE ACTION',
    'BOATING WHILE IMPAIRED': 'ALCOHOL RELATED',
    'BOMB-SUSPICIOUS ITEM FOUND': 'BOMB RELATED',
    'BOMB THREAT': 'BOMB RELATED',
    'BREAK/ENTER COMMERCIAL': 'BREAK / ENTER',
    'BREAK/ENTER RESIDENTIAL-OCCUPIED': 'BREAK / ENTER',
    'BREAK/ENTER RESIDENTIAL-UNOCCUPIED': 'BREAK / ENTER',
    'BREAK/ENTER VENDING MACHINES': 'BREAK / ENTER',
    'CANINE DEFECATION': 'ANIMAL RELATED',
    'CARELESS/RECKLESS DRIVING': 'TRAFFIC RELATED',
    'CARRYING CONCEALED WEAPON': 'WEAPON RELATED',
    'CHECK THE WELFARE OF': 'POLICE ACTION',
    'CITIZEN CONTACT': 'POLICE ACTION',
    'COMMUNICATING THREATS-OTHER': 'THREATS',
    'COMMUNICATING THREATS-PERSON': 'THREATS',
    'CPTED ANALYSIS': 'POLICE ACTION',
    'CRIME SCENE NEEDED': 'POLICE ACTION',
    'CRITICAL INCIDENT': 'CRITICAL INCIDENT',
    'CRITICAL INCIDENT CIVIL UNREST': 'CRITICAL INCIDENT',
    'CRITICAL INCIDENT CODE AT AIRPORT': 'CRITICAL INCIDENT',
    'CRITICAL INCIDENT SWAT': 'CRITICAL INCIDENT',
    'DEATH INVESTIGATION': 'DEATH RELATED',
    'DEATH-NATURAL': 'DEATH RELATED',
    'DISABLED BOATER': 'LAKE INCIDENT',
    'DISCHARGING A FIREARM': 'WEAPON RELATED',
    'DISTURBANCE': 'PUBLIC DISTURBANCE',
    'DOMESTIC DISTURBANCE': 'DOMESTIC INCIDENT',
    'DOMESTIC PROPERTY RECOVERY': 'DOMESTIC INCIDENT',
    'DOMESTIC TRESPASS': 'DOMESTIC INCIDENT',
    'DV-ADW- WITH INJURY': 'DOMESTIC INCIDENT',
    'DV-ADW-NO INJURY': 'DOMESTIC INCIDENT',
    'DV-COMMUNICATING THREATS-OTHER': 'DOMESTIC INCIDENT',
    'DV-COMMUNICATING THREATS-PERSON': 'DOMESTIC INCIDENT',
    'DOMESTIC VIOLENCE-PHYSICAL ASSAULT': 'DOMESTIC INCIDENT',
    'DV-VIOLATION OF LEGAL ORDER': 'DOMESTIC INCIDENT',
    'DRAG RACING': 'TRAFFIC RELATED',
    'DWI': 'ALCOHOL RELATED',
    'DRIVING WHILE LICENSE REVOKED': 'TRAFFIC RELATED',
    'DRUG PARAPHERNALIA-FOUND/PICKUP': 'DRUG RELATED',
    'DRUG POSSESSION-SUBSTANCE/PARAPHERNALIA': 'DRUG RELATED',
    'DRUG PRESCRIPTION-FRAUD': 'DRUG RELATED',
    'ESCORT': 'SEX RELATED',
    'EXTORTION/BLACKMAIL': 'POLICE ACTION',
    'FELINE NUISANCE': 'ANIMAL RELATED',
    'FIGHT': 'FIGHT',
    'FIGHT-CROWD': 'FIGHT',
    'FIRE CASE/INV': 'POLICE ACTION',
    'FOOT PURSUIT': 'POLICE ACTION',
    'FOUND PROPERTY': 'PROPERTY RELATED',
    'FRAUD/FORGERY': 'THEFT',
    'GRAFFITI': 'PUBLIC DISTURBANCE',
    'HARASSING PHONE CALLS': 'PUBLIC DISTURBANCE',
    'HIT & RUN-FATALITY': 'HIT AND RUN',
    'HIT & RUN-IN ROADWAY-PROPERTY DAMAGE': 'HIT AND RUN',
    'HIT & RUN-NON ROADWAY-PROPERTY DAMAGE': 'HIT AND RUN',
    'HIT & RUN-PERSONAL INJURY': 'HIT AND RUN',
    'HOMELESS PEOPLE': 'PUBLIC DISTURBANCE',
    'ILLEGAL PARKING': 'TRAFFIC RELATED',
    'INDECENT EXPOSURE': 'SEX RELATED',
    'INJURED ANIMAL': 'ANIMAL RELATED',
    'INJURY TO REAL/PERSONAL PROPERTY': 'PROPERTY RELATED',
    'JUVENILE-WEAPON AT SCHOOL': 'WEAPON RELATED',
    'KIDNAPPING': 'KIDNAPPING',
    'KIDNAPPING-JUVENILE-STRANGER': 'KIDNAPPING',
    'LAKE ABANDONED BOAT': 'LAKE INCIDENT',
    'LAKE ACCIDENT PERSONAL INJURY': 'LAKE INCIDENT',
    'LAKE ACCIDENT PROPERTY DAMAGE': 'LAKE INCIDENT',
    'LAKE ASSIST OTHER JURISDICTIONS': 'LAKE INCIDENT',
    'LAKE CHECK CHANNEL MARKER': 'LAKE INCIDENT',
    'LAKE ILLEGAL WASTE OR FUEL DISCHARGE': 'LAKE INCIDENT',
    'LAKE MEDICAL ASSISTANCE': 'LAKE INCIDENT',
    'LAKE NAVIGATIONAL HAZARD': 'LAKE INCIDENT',
    'LAKE RECKLESS OPERATION': 'LAKE INCIDENT',
    'LAKE SEARCH RESCUE/RECOVERY': 'LAKE INCIDENT',
    'LAKE WAKE VIOLATION': 'LAKE INCIDENT',
    'LARCENY': 'THEFT',
    'LARCENY FROM VEHICLE': 'THEFT',
    'LARGE ANIMAL': 'ANIMAL RELATED',
    'LOITERING': 'LOITERING',
    'LOITERING-ALCOHOL RELATED': 'LOITERING',
    'LOITERING FOR MONEY': 'LOITERING',
    'LOITERING-PROSTITUTION RELATED': 'LOITERING',
    'LOITERING-SALE/PURCHASE DRUGS': 'LOITERING',
    'LOST PROPERTY': 'PROPERTY RELATED',
    'MISSING PERSON': 'MISSING PERSON(S)',
    'MISSING PERSON-RUNAWAY': 'MISSING PERSON(S)',
    'MISSING PERSON-SPEC NEEDS/CHILD': 'MISSING PERSON(S)',
    'MISSING PERSONS RECOVERY': 'MISSING PERSON(S)',
    'NOISE COMPLAINT': 'PUBLIC DISTURBANCE',
    'NOISE COMPLAINT-CROWD': 'PUBLIC DISTURBANCE',
    'NOISE COMPLAINT-FIREWORKS': 'PUBLIC DISTURBANCE',
    'NO OPERATOR LICENSE': 'TRAFFIC RECOVERY',
    'NOTIFY': 'POLICE ACTION',
    'OVERDOSE': 'DRUG RELATED',
    'OWNER SURRENDER': 'POLICE ACTION',
    'PEEPING TOM': 'PUBLIC DISTURBANCE',
    'PERSON DOWN/PUBLIC ACCIDENT': 'PUBLIC DISTURBANCE',
    'PICK UP PROPERTY OR EVIDENCE': 'POLICE ACTION',
    'PORNOGRAPHY': 'SEX RELATED',
    'PROSTITUTION': 'SEX RELATED',
    'PROSTITUTION STING OR ARREST': 'SEX RELATED',
    'PUBLIC URINATION': 'PUBLIC DISTURBANCE',
    'ROAD BLOCKAGE': 'TRAFFIC RELATED',
    'ROBBERY FROM BUSINESS': 'THEFT',
    'ROBBERY FROM BUSINESS-ARMED': 'THEFT',
    'ROBBERY FROM PERSON': 'THEFT',
    'ROBBERY FROM PERSON-ARMED': 'THEFT',
    'SEXUALLY ORIENTED BUSINESS': 'SEX RELATED',
    'SPECIAL EVENT': 'POLICE ACTION',
    'STALKING': 'PUBLIC DISTURBANCE',
    'STOLEN VEHICLE': 'THEFT',
    'STRAY ANIMAL': 'ANIMAL RELATED',
    'SUSPICIOUS-AIRCRAFT': 'SUSPICIOUS ACTIVITY',
    'SUSPICIOUS PERSON/PROWLER': 'SUSPICIOUS ACTIVITY',
    'SUSPICIOUS PROPERTY': 'SUSPICIOUS ACTIVITY',
    'SUSPICIOUS VEHICLE OCCUPIED': 'SUSPICIOUS ACTIVITY',
    'SUSPICIOUS VEHICLE UNOCCUPIED': 'SUSPICIOUS ACTIVITY',
    'TOWED VEHICLE-ADVISED EVENT': 'TRAFFIC RELATED',
    'TRAFFIC CONTROL/MALFUNCTION': 'TRAFFIC RELATED',
    'TRASH/LITTERING': 'PUBLIC DISTURBANCE',
    'TRESPASS': 'PUBLIC DISTURBANCE',
    'TRUANCY': 'PUBLIC DISTURBANCE',
    'UNAUTHORIZED USE OF VEHICLE': 'TRAFFIC RELATED',
    'VEHICLE DISABLED IN ROADWAY': 'TRAFFIC RELATED',
    'VEHICLE DISABLED NOT IN ROADWAY': 'TRAFFIC RELATED',
    'VEHICLE PURSUIT': 'TRAFFIC RELATED',
    'VEHICLE RECOVERY': 'POLICE ACTION',
    'WILD ANIMAL': 'ANIMAL RELATED',
    'WORTHLESS CHECKS': 'THEFT',
    'ZONE CHECK': 'POLICE ACTION',
}

class CallScraper(NewsItemListDetailScraper):
    schema_slugs = ('police-calls',)
    has_detail = False
    parse_list_re = re.compile(r'<tr[^>]*>\s*<td>(?P<datetime>\d\d?/\d\d?/\d{4} \d\d?:\d\d:\d\d [AP]M)</td><td>(?P<division>[^>]*)</td><td>(?P<address>[^>]*)\s*</td><td>(?P<event>[^>]*)</td><td>(?P<disposition>[^>]*)</td>\s*</tr>', re.IGNORECASE | re.DOTALL)

    def __init__(self, hours=8, *args, **kwargs):
        self.num_hours = hours
        NewsItemListDetailScraper.__init__(self, *args, **kwargs)

    def list_pages(self):
        html = self.get_html(SOURCE_URL)
        
        m = re.search(r'<input type="hidden" name="__VIEWSTATE" value="([^"]*)"', html)
        if not m:
            raise ScraperBroken('VIEWSTATE not found on %s' % self.source_url)
        viewstate = m.group(1)
        
        yield self.get_html(SOURCE_URL, {'__VIEWSTATE': viewstate, 'ddlEvtHours': self.num_hours, 'btnRefresh': 'Refresh'})

    def clean_list_record(self, record):
        # Save the raw address so we can use it to find duplicate records in
        # the future.
        address = smart_title(record['address'].strip().replace('&amp;', '&').replace('&nbsp;', ' ')).strip()
        record['raw_address'] = address
        record['address'] = address_to_block(clean_address(address))

        record['disposition'] = record['disposition'].replace('&amp;', '&').replace('&nbsp;', ' ').strip() or 'Not available'
        record['event'] = record['event'].replace('&amp;', '&').replace('&nbsp;', ' ').strip()
        item_date = parse_date(record['datetime'], '%m/%d/%Y %I:%M:%S %p', return_datetime=True)
        record['item_date'] = item_date.date()
        record['item_time'] = item_date.time()

        # Normalize this value.
        if record['disposition'] == 'CANCCOMM':
            record['disposition'] = 'CANCELLED BY COMMUNICATIONS'

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['item_date'])
            qs = qs.by_attribute(self.schema_fields['raw_address'], record['address'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            self.logger.debug('Record already exists')
            return

        division = self.get_or_create_lookup('division', list_record['division'], list_record['division'])
        event = self.get_or_create_lookup('event', list_record['event'], list_record['event'])
        disposition = self.get_or_create_lookup('disposition', list_record['disposition'], list_record['disposition'])
        category_name = CATEGORIES[event.code.upper().strip()]
        category = self.get_or_create_lookup('category', capfirst(category_name.lower()), category_name)

        attributes = {
            'raw_address': list_record['address'],
            'division': division.id,
            'disposition': disposition.id,
            'event': event.id,
            'event_time': list_record['item_time'],
            'category': category.id
        }
        self.create_newsitem(
            attributes,
            title=event.name,
            item_date=list_record['item_date'],
            location_name=list_record['address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    CallScraper().update()
