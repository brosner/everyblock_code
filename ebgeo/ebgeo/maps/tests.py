import unittest
from extent import transform_extent, city_from_extent
from tess import tessellate, cover_region, cover_city
from shortcuts import get_all_tile_coords, extent_in_map_srs, city_extent_in_map_srs, get_locator_scale

class ExtentTestCase(unittest.TestCase):
    def test_transform_extent(self):
        extent = (-87.9, 41.9, -87.8, 42.0)
        expected = (-9784983.241, 5146011.679, -9773851.292, 5160979.444)
        transformed = transform_extent(extent, 900913)
        for i in xrange(4):
            self.assertAlmostEqual(transformed[i], expected[i], places=3)

    def test_city_from_extent(self):
        extent = (-87.7433, 41.9243, -87.6927, 41.9511)
        self.assertEqual('chicago', city_from_extent(extent))

    def test_city_from_extent_non_unique_match(self):
        # Extent overlaps Philly and NYC, but moreso Philly
        extent = (-75.1087, 40.0048, -74.2267, 40.5173)
        self.assertEqual('philly', city_from_extent(extent))

    def test_city_from_extent_no_initial_overlap(self):
        # Extent to the south-west of San Jose
        extent = (-122.5669, 37.0204, -122.2787, 37.1912)
        self.assertEqual('sanjose', city_from_extent(extent))

class TessellateTestCase(unittest.TestCase):
    def _test_tessellation(self, fn, extent, radius, expected, places=3):
        actual = list(fn(extent, radius))
        for i, (x, y) in enumerate(actual):
            self.assertAlmostEqual(expected[i][0], x, places=places)
            self.assertAlmostEqual(expected[i][1], y, places=places)

    def test_tessellate(self):
        extent = (0, 0, 100, 100)
        radius = 30
        expected = [
            (25.980762113533157, 15.000000000000002),
            (77.942286340599466, 15.000000000000002),
            (0.0, 60.0),
            (51.961524227066306, 60.0),
            (103.92304845413261, 60.0),
            (25.980762113533157, 105.0),
            (77.942286340599466, 105.0)]
        self._test_tessellation(tessellate, extent, radius, expected)

    def test_cover_region(self):
        extent = (-87.7220, 41.9282, -87.7020, 41.9402)
        radius = 0.2 * 3 # in kilometers, 3 Chicago city blocks
        expected = [
            (-87.717332216860044, 41.930204961746526),
            (-87.707996650580171, 41.930204961746526),
            (-87.698661084300312, 41.930204961746526),
            (-87.721999999999966, 41.936219468889561),
            (-87.712664433720107, 41.936219468889561),
            (-87.703328867440248, 41.936219468889561),
            (-87.717332216860044, 41.942233408877819),
            (-87.707996650580171, 41.942233408877819),
            (-87.698661084300312, 41.942233408877819)]
        self._test_tessellation(cover_region, extent, radius, expected, places=5)

    def test_cover_city(self):
        expected = [
            (-87.551111071672324, 41.678109980749085),
            (-87.784500228668932, 41.778672990728793),
            (-87.628907457337846, 41.778672990728793),
            (-87.706703843003382, 41.879078553274987),
            (-87.784500228668932, 41.979326607041052)]
        self._test_tessellation(cover_city, 'chicago', 10, expected, places=5)

class ShortcutsTestCase(unittest.TestCase):
    def _compare_extents(self, expected, actual, places=3):
        for i, value in enumerate(actual):
            self.assertAlmostEqual(expected[i], value, places=places)
    
    def test_get_all_tile_coords(self):
        expected = [(68, 36, 0),
                    (73, 36, 0),
                    (78, 36, 0),
                    (68, 41, 0),
                    (73, 41, 0),
                    (78, 41, 0),
                    (68, 46, 0),
                    (73, 46, 0),
                    (78, 46, 0)]
        self.assertEqual(expected, list(get_all_tile_coords('main', 'chicago', levels=(0, 1))))

    def test_extent_in_map_srs(self):
        extent = (-87.721999999999994,
                  41.928199999999997,
                  -87.701999999999998,
                  41.940199999999997)

        expected = (-9765168.3713675346,
                    5150230.2126926854,
                    -9762941.9815516714,
                    5152025.8988631964)

        actual = extent_in_map_srs(extent)

        self._compare_extents(expected, actual)

    def test_city_extent_in_map_srs(self):
        expected = (-9789446.3730731141,
                    5107883.1729132505,
                    -9743141.6950437613,
                    5164430.3004190186)

        actual = city_extent_in_map_srs('chicago')

        self._compare_extents(expected, actual)

    def test_get_locator_scale(self):
        self.assertAlmostEqual(2137215,
                               get_locator_scale('chicago'),
                               places=0)

if __name__ == '__main__':
    unittest.main()
