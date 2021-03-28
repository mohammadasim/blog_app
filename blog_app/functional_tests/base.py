import os

from selenium import webdriver
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


class FunctionalTests(StaticLiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()
        self.staging_server = os.environ.get('STAGING_SERVER')
        if self.staging_server:
            self.live_server_url = 'http://'+self.staging_server

    def tearDown(self):
        self.browser.quit()
