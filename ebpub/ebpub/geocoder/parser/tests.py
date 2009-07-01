"""
Tests for address parsing.

The LocationTestCase class contains both hand-written tests and a metaclass
that auto-generates tests based on some sample data.
"""

from ebpub.geocoder.parser.parsing import parse, address_combinations, ParsingError, Location
import unittest

class AutoLocationMetaclass(type):
    """
    Metaclass that adds a test method for every combination of test data
    (defined in TEST_DATA).
    """
    def __new__(cls, name, bases, attrs):
        TEST_DATA = (
            # token type, (one-word sample, two-word sample, three-word sample, ...)
            ('number', ('228',)),
            ('pre_dir', ('S',)),
            ('street', ('BROADWAY', 'OLD MILL', 'MARTIN LUTHER KING', 'MARTIN LUTHER KING JR', 'DR MARTIN LUTHER KING JR')),
            ('suffix', ('AVE',)),
            ('post_dir', ('S',)),
            ('city', ('CHICAGO', 'SAN FRANCISCO', 'NEW YORK CITY', 'OLD NEW YORK CITY')),
            ('state', ('IL', 'NEW HAMPSHIRE')),
            ('zip', ('60604',)),
        )
        for token_types in address_combinations():
            test_input = []
            expected = Location()
            for t_type, samples in TEST_DATA:
                count = token_types.count(t_type)
                if count:
                    test_input.append(samples[count-1])
                    expected[t_type] = samples[count-1]

            # Take the normalization into account.
            if expected['state'] == 'NEW HAMPSHIRE':
                expected['state'] = 'NH'

            location = ' '.join(test_input)
            func = lambda self: self.assertParseContains(location, expected)
            func.__doc__ = location
            attrs['test_%s' % '_'.join(token_types)] = func

        return type.__new__(cls, name, bases, attrs)

class LocationTestCase(unittest.TestCase):
    __metaclass__ = AutoLocationMetaclass

    # def assertParses(self, location, expected):
    #     try:
    #         actual = [dict(result) for result in parse(location)]
    #         try:
    #             self.assertEqual(actual, expected)
    #         except AssertionError, e:
    #             raise AssertionError("%r: %s" % (location, e))
    #     except ParsingError, e:
    #         self.fail(e)

    def assertParseContains(self, location, contains):
        # Because the parser is overly greedy and gives many possible
        # responses, it keeps the unit tests tidier and less brittle if we
        # just list one important parse result that we expect, rather than
        # listing every single test result.
        try:
            actual = [dict(result) for result in parse(location)]
        except ParsingError, e:
            self.fail(e)
        else:
            self.assert_(contains in actual, '%r not in %r' % (contains, actual))

    def test_saint_louis(self):
        self.assertParseContains('11466 S Saint Louis Ave, Chicago, IL, 60655',
            {'number': '11466', 'pre_dir': 'S', 'street': 'SAINT LOUIS', 'suffix': 'AVE', 'post_dir': None, 'city': 'CHICAGO', 'state': 'IL', 'zip': '60655'},
        )

    def test_st_louis_ave(self):
        self.assertParseContains('11466 S St Louis Ave',
            {'number': '11466', 'pre_dir': 'S', 'street': 'ST LOUIS', 'suffix': 'AVE', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_st_louis_st(self):
        self.assertParseContains('11466 S St Louis St',
            {'number': '11466', 'pre_dir': 'S', 'street': 'ST LOUIS', 'suffix': 'ST', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_numbered_street1(self):
        self.assertParseContains('2 W 111th Pl',
            {'number': '2', 'pre_dir': 'W', 'street': '111TH', 'suffix': 'PL', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_numbered_street2(self):
        self.assertParseContains('260 W 44th St',
            {'number': '260', 'pre_dir': 'W', 'street': '44TH', 'suffix': 'ST', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_numbered_street3(self):
        self.assertParseContains('260 W 44th, New York, NY 10036',
            {'number': '260', 'pre_dir': 'W', 'street': '44TH', 'suffix': None, 'post_dir': None, 'city': 'NEW YORK', 'state': 'NY', 'zip': '10036'},
        )

    def test_numbered_street4(self):
        self.assertParseContains('1 5th Ave, New York, NY 10003',
            {'number': '1', 'pre_dir': None, 'street': '5TH', 'suffix': 'AVE', 'post_dir': None, 'city': 'NEW YORK', 'state': 'NY', 'zip': '10003'},
        )

    def test_numbered_street5(self):
        self.assertParseContains('329 50 ST, MANHATTAN',
            {'number': '329', 'pre_dir': None, 'street': '50TH', 'suffix': 'ST', 'post_dir': None, 'city': 'MANHATTAN', 'state': None, 'zip': None},
        )

    def test_numbered_street6(self):
        self.assertParseContains('329 41 ST, MANHATTAN',
            {'number': '329', 'pre_dir': None, 'street': '41ST', 'suffix': 'ST', 'post_dir': None, 'city': 'MANHATTAN', 'state': None, 'zip': None},
        )

    def test_numbered_street7(self):
        self.assertParseContains('329 42 ST, MANHATTAN',
            {'number': '329', 'pre_dir': None, 'street': '42ND', 'suffix': 'ST', 'post_dir': None, 'city': 'MANHATTAN', 'state': None, 'zip': None},
        )

    def test_numbered_street8(self):
        self.assertParseContains('329 43 ST, MANHATTAN',
            {'number': '329', 'pre_dir': None, 'street': '43RD', 'suffix': 'ST', 'post_dir': None, 'city': 'MANHATTAN', 'state': None, 'zip': None},
        )

    def test_junior(self):
        self.assertParseContains('3624 S. John Hancock Jr. Road',
            {'number': '3624', 'pre_dir': 'S', 'street': 'JOHN HANCOCK JR', 'suffix': 'RD', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    # The test_perl* tests were copied from the unit tests for the CPAN
    # Geo::StreetAddress module.
    def test_perl1(self):
        self.assertParseContains('1005 Gravenstein Hwy 95472',
            {'number': '1005', 'pre_dir': None, 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': None, 'city': None, 'state': None, 'zip': '95472'},
        )

    def test_perl2(self):
        self.assertParseContains('1005 Gravenstein Hwy, 95472',
            {'number': '1005', 'pre_dir': None, 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': None, 'city': None, 'state': None, 'zip': '95472'},
        )

    def test_perl3(self):
        self.assertParseContains('1005 Gravenstein Hwy N, 95472',
            {'number': '1005', 'pre_dir': None, 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': 'N', 'city': None, 'state': None, 'zip': '95472'},
        )

    def test_perl4(self):
        self.assertParseContains('1005 Gravenstein Highway North, 95472',
            {'number': '1005', 'pre_dir': None, 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': 'N', 'city': None, 'state': None, 'zip': '95472'},
        )

    def test_perl5(self):
        self.assertParseContains('1005 N Gravenstein Highway, Sebastopol, CA',
            {'number': '1005', 'pre_dir': 'N', 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': None, 'city': 'SEBASTOPOL', 'state': 'CA', 'zip': None},
        )

    # def test_perl6(self):
    #     self.assertParses('1005 N Gravenstein Highway, Suite 500, Sebastopol, CA', [{
    #         'number': '1005',
    #         'pre_dir': 'N',
    #         'street': 'GRAVENSTEIN',
    #         'suffix': 'HWY',
    #         'post_dir': None,
    #         'city': 'SEBASTOPOL',
    #         'state': 'CA',
    #         'zip': None,
    #     }])
    # 
    # def test_perl7(self):
    #     self.assertParses('1005 N Gravenstein Hwy Suite 500 Sebastopol, CA', [{
    #         'number': '1005',
    #         'pre_dir': 'N',
    #         'street': 'GRAVENSTEIN',
    #         'suffix': 'HWY',
    #         'post_dir': None,
    #         'city': 'SEBASTOPOL',
    #         'state': 'CA',
    #         'zip': None,
    #     }])

    def test_perl8(self):
        self.assertParseContains('1005 N Gravenstein Highway, Sebastopol, CA, 95472',
            {'number': '1005', 'pre_dir': 'N', 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': None, 'city': 'SEBASTOPOL', 'state': 'CA', 'zip': '95472'},
        )

    def test_perl9(self):
        self.assertParseContains('1005 N Gravenstein Highway Sebastopol CA 95472',
            {'number': '1005', 'pre_dir': 'N', 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': None, 'city': 'SEBASTOPOL', 'state': 'CA', 'zip': '95472'},
        )

    def test_perl10(self):
        self.assertParseContains('1005 Gravenstein Hwy N Sebastopol CA',
            {'number': '1005', 'pre_dir': None, 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': 'N', 'city': 'SEBASTOPOL', 'state': 'CA', 'zip': None},
        )

    def test_perl11(self):
        self.assertParseContains('1005 Gravenstein Hwy N, Sebastopol CA',
            {'number': '1005', 'pre_dir': None, 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': 'N', 'city': 'SEBASTOPOL', 'state': 'CA', 'zip': None},
        )

    def test_perl13(self):
        self.assertParseContains('1005 Gravenstein Hwy, North Sebastopol CA',
            {'number': '1005', 'pre_dir': None, 'street': 'GRAVENSTEIN', 'suffix': 'HWY', 'post_dir': None, 'city': 'NORTH SEBASTOPOL', 'state': 'CA', 'zip': None},
        )

    def test_perl18(self):
        self.assertParseContains('1600 Pennsylvania Ave. Washington DC',
            {'number': '1600', 'pre_dir': None, 'street': 'PENNSYLVANIA', 'suffix': 'AVE', 'post_dir': None, 'city': 'WASHINGTON', 'state': 'DC', 'zip': None},
        )

    def test_perl21(self):
        self.assertParseContains('100 South St, Philadelphia, PA',
            {'number': '100', 'pre_dir': None, 'street': 'SOUTH', 'suffix': 'ST', 'post_dir': None, 'city': 'PHILADELPHIA', 'state': 'PA', 'zip': None},
        )

    def test_perl22(self):
        self.assertParseContains('100 S.E. Washington Ave, Minneapolis, MN',
            {'number': '100', 'pre_dir': 'SE', 'street': 'WASHINGTON', 'suffix': 'AVE', 'post_dir': None, 'city': 'MINNEAPOLIS', 'state': 'MN', 'zip': None},
        )

    def test_perl23(self):
        self.assertParseContains('3813 1/2 Some Road, Los Angeles, CA',
            {'number': '3813', 'pre_dir': None, 'street': 'SOME', 'suffix': 'RD', 'post_dir': None, 'city': 'LOS ANGELES', 'state': 'CA', 'zip': None},
        )

    def test_nyc_borough(self):
        self.assertParseContains("187 Bedord Ave, Brooklyn, NY",
            {'number': '187', 'pre_dir': None, 'street': 'BEDORD', 'suffix': 'AVE', 'post_dir': None, 'city': 'BROOKLYN', 'state': 'NY', 'zip': None},
        )

    def test_avenue_b_nyc(self):
        self.assertParseContains("51 Avenue B, New York, NY",
            {'number': '51', 'pre_dir': None, 'street': 'AVENUE B', 'suffix': None, 'post_dir': None, 'city': 'NEW YORK', 'state': 'NY', 'zip': None},
        )

    def test_e20th_st_nyc(self):
        self.assertParseContains("31 East 20th Street, New York, NY",
            {'number': '31', 'pre_dir': 'E', 'street': '20TH', 'suffix': 'ST', 'post_dir': None, 'city': 'NEW YORK', 'state': 'NY', 'zip': None},
        )

    def test_fifth_st_standardization(self):
        self.assertParseContains('175 Fifth St Brooklyn NY',
            {'number': '175', 'pre_dir': None, 'street': '5TH', 'suffix': 'ST', 'post_dir': None, 'city': 'BROOKLYN', 'state': 'NY', 'zip': None},
        )

    def test_bronx_standardization1(self):
        self.assertParseContains('123 Main St Bronx',
            {'number': '123', 'pre_dir': None, 'street': 'MAIN', 'suffix': 'ST', 'post_dir': None, 'city': 'THE BRONX', 'state': None, 'zip': None},
        )

    def test_bronx_standardization2(self):
        self.assertParseContains('123 Main St, The Bronx',
            {'number': '123', 'pre_dir': None, 'street': 'MAIN', 'suffix': 'ST', 'post_dir': None, 'city': 'THE BRONX', 'state': None, 'zip': None},
        )

    def test_broadway_simple(self):
        self.assertParseContains('321 BROADWAY, MANHATTAN',
            {'number': '321', 'pre_dir': None, 'street': 'BROADWAY', 'suffix': None, 'post_dir': None, 'city': 'MANHATTAN', 'state': None, 'zip': None},
        )

    def test_staten_island1(self):
        self.assertParseContains('321 BROADWAY, STATEN ISLAND',
            {'number': '321', 'pre_dir': None, 'street': 'BROADWAY', 'suffix': None, 'post_dir': None, 'city': 'STATEN ISLAND', 'state': None, 'zip': None},
        )

    def test_staten_island2(self):
        self.assertParseContains('349 TRAVIS AVENUE, STATEN ISLAND',
            {'number': '349', 'pre_dir': None, 'street': 'TRAVIS', 'suffix': 'AVE', 'post_dir': None, 'city': 'STATEN ISLAND', 'state': None, 'zip': None},
        )

    def test_queens_address_range(self):
        self.assertParseContains('25-82 MAIN ST, QUEENS',
            {'number': '25', 'pre_dir': None, 'street': 'MAIN', 'suffix': 'ST', 'post_dir': None, 'city': 'QUEENS', 'state': None, 'zip': None},
        )

    def test_ft_washington_ave(self):
        self.assertParseContains('270 FT WASHINGTON AVENUE, MANHATTAN',
            {'number': '270', 'pre_dir': None, 'street': 'FT WASHINGTON', 'suffix': 'AVE', 'post_dir': None, 'city': 'MANHATTAN', 'state': None, 'zip': None},
        )

    def test_east_broadway(self):
        self.assertParseContains('183 EAST BROADWAY, MANHATTAN',
            {'number': '183', 'pre_dir': None, 'street': 'EAST BROADWAY', 'suffix': None, 'post_dir': None, 'city': 'MANHATTAN', 'state': None, 'zip': None},
        )

    def test_one_nob_hill(self):
        self.assertParseContains('1 Nob Hill',
            {'number': '1', 'pre_dir': None, 'street': 'NOB HILL', 'suffix': None, 'post_dir': None, 'city': None, 'state': None, 'zip': None}
        )

    def test_west_irving_park(self):
        self.assertParseContains('1234 W IRVING PARK',
            {'number': '1234', 'pre_dir': 'W', 'street': 'IRVING PARK', 'suffix': None, 'post_dir': None, 'city': None, 'state': None, 'zip': None}
        )

    def test_half_address1(self):
        self.assertParseContains('123 1/2 MAIN ST',
            {'number': '123', 'pre_dir': None, 'street': 'MAIN', 'suffix': 'ST', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_half_address2(self):
        self.assertParseContains('123 I/2 MAIN ST',
            {'number': '123', 'pre_dir': None, 'street': 'MAIN', 'suffix': 'ST', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_hyphen_space_address1(self):
        self.assertParseContains('123 - 125 MAIN ST',
            {'number': '123', 'pre_dir': None, 'street': 'MAIN', 'suffix': 'ST', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_hyphen_space_address2(self):
        self.assertParseContains('123- 125 MAIN ST',
            {'number': '123', 'pre_dir': None, 'street': 'MAIN', 'suffix': 'ST', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_hyphen_space_address3(self):
        self.assertParseContains('123 -125 MAIN ST',
            {'number': '123', 'pre_dir': None, 'street': 'MAIN', 'suffix': 'ST', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_multiple_hyphen_space_address(self):
        self.assertParseContains('123--125 MAIN ST',
            {'number': '123', 'pre_dir': None, 'street': 'MAIN', 'suffix': 'ST', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_letter_in_address(self):
        self.assertParseContains('2833A W CHICAGO AVE',
            {'number': '2833', 'pre_dir': 'W', 'street': 'CHICAGO', 'suffix': 'AVE', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_letter_in_address_range(self):
        self.assertParseContains('2833A-2835A W CHICAGO AVE',
            {'number': '2833', 'pre_dir': 'W', 'street': 'CHICAGO', 'suffix': 'AVE', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_mies_van_der_rohe_wy(self):
        self.assertParseContains('830 N MIES VAN DER ROHE WY',
            {'number': '830', 'pre_dir': 'N', 'street': 'MIES VAN DER ROHE', 'suffix': 'WAY', 'post_dir': None, 'city': None, 'state': None, 'zip': None},
        )

    def test_the_bronx_address1(self):
        self.assertParseContains('823 East 147th St, The Bronx',
            {'number': '823', 'pre_dir': 'E', 'street': '147TH', 'suffix': 'ST', 'post_dir': None, 'city': 'THE BRONX', 'state': None, 'zip': None},
        )

    def test_the_bronx_address2(self):
        self.assertParseContains('1401 Grand Concourse, The Bronx',
            {'number': '1401', 'pre_dir': None, 'street': 'GRAND CONCOURSE', 'suffix': None, 'post_dir': None, 'city': 'THE BRONX', 'state': None, 'zip': None},
        )

    def test_the_bronx_address3(self):
        self.assertParseContains('1110 Bronx River Ave, The Bronx',
            {'number': '1110', 'pre_dir': None, 'street': 'BRONX RIVER', 'suffix': 'AVE', 'post_dir': None, 'city': 'THE BRONX', 'state': None, 'zip': None},
        )

if __name__ == "__main__":
    unittest.main()
