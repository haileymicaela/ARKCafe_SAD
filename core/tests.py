from django.test import TestCase

class HomeTest(TestCase):
    def test_home(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_fail(self):
        self.assertEqual(1, 2)