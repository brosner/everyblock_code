from django.test import TestCase
from django.contrib.gis.geos import Point
from ebpub.metros.models import Metro

pt_in_chicago = Point((-87.68489561595398, 41.852929331184384)) # point in center of Chicago
pt_in_chi_bbox = Point((-87.83384627077956, 41.85365447332586)) # point just west of Chicago's border but due south of O'Hare
pt_in_lake_mi = Point((-86.99514699540548, 41.87468001919902)) # point way out in Lake Michigan

class MetroTest(TestCase):
    fixtures = ['metros']
    
    def test_point_in_metro(self):
        """
        Tests finding a metro with a point contained by its boundary
        """
        self.assertEquals(Metro.objects.containing_point(pt_in_chicago).name, 'Chicago')

    def test_point_in_bbox_not_in_metro(self):
        """
        Tests with a point in the metro's bounding box but not in its boundary
        """
        self.assertRaises(Metro.DoesNotExist, Metro.objects.containing_point, pt_in_chi_bbox)

    def test_point_not_in_metro(self):
        """
        Tests with a point not in any metro
        """
        self.assertRaises(Metro.DoesNotExist, Metro.objects.containing_point, pt_in_lake_mi)

class MetroViewsTest(TestCase):
    fixtures = ['metros']

    def test_lookup_metro_success(self):
        """
        Tests getting a successful JSON response from a lng/lat query
        """
        response = self.client.get('/metros/lookup/', {'lng': pt_in_chicago.x, 'lat': pt_in_chicago.y}) 
        self.assertContains(response, 'Chicago', status_code=200)
        self.assertEqual(response['content-type'], 'application/javascript')

    def test_lookup_metro_in_bbox_fails(self):
        """
        Tests getting a 404 from a lng/lat query not quite in the metro
        """
        response = self.client.get('/metros/lookup/', {'lng': pt_in_chi_bbox.x, 'lat': pt_in_chi_bbox.y}) 
        self.assertEqual(response.status_code, 404)

    def test_lookup_metro_fails(self):
        """
        Tests getting a 404 from a lng/lat query not in any metro
        """
        response = self.client.get('/metros/lookup/', {'lng': pt_in_lake_mi.x, 'lat': pt_in_lake_mi.y}) 
        self.assertEqual(response.status_code, 404)
