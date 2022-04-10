import argparse
import functools
import os
import sys
import time

# Generated by Selenium IDE
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys


class NoImplicitWait(object):
    """
    Example usage:

    with NoImplicitWait(driver, 0):
        driver.find_element(By.ID, 'element-that-might-not-be-there')
    """

    def __init__(self, driver, new_wait=0):
        self.driver = driver
        self.original_wait = driver.timeouts.implicit_wait
        self.new_wait = new_wait

    def __enter__(self):
        self.driver.implicitly_wait(self.new_wait)

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.driver.implicitly_wait(self.original_wait)


def clock_action(action_name):
    """
    Decorator to measure time taken to perform
    a function. The timing is stored in the wrapped
    object, assumed to be first args to wrapped function.
    :return:
    """

    def wrap(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            obj = args[0]
            start = time.time()
            retval = func(*args, **kwargs)
            elapsed = time.time() - start
            obj.timings[action_name] = elapsed
            return retval

        return wrapper

    return wrap


class PagePerfTimer(object):

    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password
        self.timings = {}

        """Start web driver"""
        chrome_options = webdriver.ChromeOptions()
        if os.environ.get('SELENIUM_HEADLESS'):
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(180)
        self.wait = WebDriverWait(self.driver, 180)

    def find_login_button(self):
        with NoImplicitWait(self.driver, 0):
            try:
                return self.driver.find_element(By.NAME, "login")
            except NoSuchElementException:
                return None

    def find_sign_in_with_email(self):
        with NoImplicitWait(self.driver, 0):
            try:
                return self.driver.find_element(By.XPATH, "//a[contains(., 'Sign in with email')]")
            except NoSuchElementException:
                return None

    def is_able_to_login(self, driver):
        if self.find_login_button():
            return True
        elif self.find_sign_in_with_email():
            return True
        else:
            return False

    @clock_action("login_page_load")
    def load_galaxy_login(self):
        # Open Galaxy window
        self.driver.get(f"{self.server}/login")
        # Wait for username entry to appear
        self.wait.until(self.is_able_to_login)

    @clock_action("home_page_load")
    def login_to_galaxy_homepage(self):
        elem = self.find_sign_in_with_email()
        # if sign in with email is available, this is galaxy-au's customised page.
        if elem:
            elem.click()
        # Click username textbox
        self.driver.find_element(By.NAME, "login").click()
        # Type in username
        self.driver.find_element(By.NAME, "login").send_keys(self.username)
        # Type in password
        self.driver.find_element(By.NAME, "password").send_keys(self.password)
        # Submit login form
        self.driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
        # Wait for tool search box to appear
        self.wait.until(expected_conditions.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='search tools']")))

    @clock_action("tool_search_load")
    def search_for_tool(self):
        # Select tool search box
        tool_search = self.driver.find_element(By.XPATH, "//input[@placeholder='search tools']")
        tool_search.click()
        # Search for BWA
        tool_search.send_keys("bwa")
        # Wait for BWA tool to appear
        self.wait.until(expected_conditions.presence_of_element_located(
            (By.XPATH,
             "//a[@href='/tool_runner?tool_id=toolshed.g2.bx.psu.edu%2Frepos%2Fdevteam%2Fbwa%2Fbwa%2F0.7.17.4']")))

    @clock_action("tool_form_load")
    def load_tool_form(self):
        # Select BWA tool
        bwa_tool = self.driver.find_element(
            By.XPATH,
            "//a[@href='/tool_runner?tool_id=toolshed.g2.bx.psu.edu%2Frepos%2Fdevteam%2Fbwa%2Fbwa%2F0.7.17.4']")
        bwa_tool.click()
        # Wait for tool form to load and execute button to appear
        self.wait.until(expected_conditions.presence_of_element_located((By.ID, "execute")))

    def run_test_sequence(self):
        self.load_galaxy_login()
        self.login_to_galaxy_homepage()
        self.search_for_tool()
        self.load_tool_form()

    def measure_timings(self):
        self.timings = {}
        try:
            self.run_test_sequence()
        finally:
            self.driver.quit()

    def print_timings(self):
        for action, time_taken in self.timings.items():
          print(f"user_flow_performance,server={self.server},action={action} time_taken={time_taken}")


def from_env_or_required(key):
    return {'default': os.environ[key]} if os.environ.get(key) else {'required': True}


def create_parser():
    parser = argparse.ArgumentParser(
        description='Measure time taken for a typical user flow from login to tool execution in Galaxy.')
    parser.add_argument('-s', '--server', default=os.environ.get('GALAXY_SERVER') or "https://usegalaxy.org.au",
                        help="Galaxy server url")
    parser.add_argument('-u', '--username', **from_env_or_required('GALAXY_USERNAME'),
                        help="Galaxy username to use (or set GALAXY_USERNAME env var)")
    parser.add_argument('-p', '--password', **from_env_or_required('GALAXY_PASSWORD'),
                        help="Password to use (or set GALAXY_PASSWORD env var)")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    perf_timer = PagePerfTimer(args.server, args.username, args.password)
    perf_timer.measure_timings()
    perf_timer.print_timings()
    return 0


if __name__ == '__main__':
    sys.exit(main())
