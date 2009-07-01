from ebpub.geocoder import SmartGeocoder, AmbiguousResult, InvalidBlockButValidStreet
import os.path
import unittest
import yaml

class GeocoderTestCase(unittest.TestCase):
    address_fields = ('address', 'city', 'zip')

    def load_fixtures(self):
        fixtures_filename = 'locations.yaml'
        locations = yaml.load(open(os.path.join(os.path.dirname(__file__), fixtures_filename)))
        for key, value in locations.items():
            pass

    def assertAddressMatches(self, expected, actual):
        unmatched_fields = []

        for field in self.address_fields:
            try:
                self.assertEqual(expected[field], actual[field])
            except AssertionError, e:
                unmatched_fields.append(field)

        if unmatched_fields:
            raise AssertionError('unmatched address fields: %s' % ', '.join(unmatched_fields))

    def assertNearPoint(self, point, other):
        try:
            self.assertAlmostEqual(point.x, other.x, places=3)
            self.assertAlmostEqual(point.y, other.y, places=3)
        except AssertionError, e:
            raise AssertionError('`point\' not near enough to `other\': %s', e)

class BaseGeocoderTestCase(unittest.TestCase):
    fixtures = ['wabash.yaml']

    def setUp(self):
        self.geocoder = SmartGeocoder(use_cache=False)

    def test_address_geocoder(self):
        address = self.geocoder.geocode('200 S Wabash')
        self.assertEqual(address['city'], 'Chicago')

    def test_address_geocoder_ambiguous(self):
        self.assertRaises(AmbiguousResult, self.geocoder.geocode, '200 Wabash')

    def test_address_geocoder_invalid_block(self):
        self.assertRaises(InvalidBlockButValidStreet, self.geocoder.geocode, '100000 S Wabash')

    def test_block_geocoder(self):
        address = self.geocoder.geocode('200 block of Wabash')
        self.assertEqual(address['city'], 'Chicago')

    def test_intersection_geocoder(self):
        address = self.geocoder.geocode('Wabash and Jackson')
        self.assertEqual(address['city'], 'CHICAGO')

if __name__ == '__main__':
    pass
