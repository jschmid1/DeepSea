import json
import logging

log = logging.getLogger(__name__)

class Bcolors(object):
    """
    Sequences for colored text
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class PrettyPrinter(object):
    """
    Console printing
    """

    # pylint: disable=unused-argument
    def add(self, name, passed, errors, warnings):
        """
        Print colored results.  Green is ok, yellow is warning and
        red is error.
        """
        # Need to make colors optional, but looks better currently
        for attr in passed.keys():
            format_str = "{:25}: {}{}{}{}".format(attr,
                                                  Bcolors.BOLD,
                                                  Bcolors.OKGREEN,
                                                  passed[attr],
                                                  Bcolors.ENDC)
            log.info("VALIDATE PASSED  " + format_str)
            print(format_str)
        for attr in errors.keys():
            format_str = "{:25}: {}{}{}{}".format(attr,
                                                  Bcolors.BOLD,
                                                  Bcolors.FAIL,
                                                  errors[attr],
                                                  Bcolors.ENDC)
            log.info("VALIDATE ERROR   " + format_str)
            print(format_str)
        for attr in warnings.keys():
            format_str = "{:25}: {}{}{}{}".format(attr,
                                                  Bcolors.BOLD,
                                                  Bcolors.WARNING,
                                                  warnings[attr],
                                                  Bcolors.ENDC)
            log.info("VALIDATE WARNING " + format_str)
            print(format_str)

    def print_result(self):
        """
        Printing happens during add
        """
        pass


class JsonPrinter(object):
    """
    API printing
    """

    def __init__(self):
        """
        Initialize result
        """
        self.result = {}

    def add(self, name, passed, errors, warnings):
        """
        Collect results
        """
        self.result[name] = {'passed': passed, 'errors': errors, 'warnings': warnings}

    def print_result(self):
        """
        Dump results as json
        """
        json.dump(self.result, sys.stdout)


