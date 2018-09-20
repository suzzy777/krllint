#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# MIT License
#
# Copyright (c) 2018 Daniel Braunwarth
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Checks and automatically fixes KRL (KUKA Robot Language) code.
"""

import os
import re
import inspect
from abc import ABC, abstractmethod

__version__ = "0.1.0"


CHECKERS = []


def register_checker(checker):
    if checker not in CHECKERS:
        CHECKERS.append(checker())
    return checker


class BaseChecker(ABC):
    @abstractmethod
    def check(self):
        pass

    @abstractmethod
    def fix(self):
        pass


################################################################################
# Checkers
################################################################################


@register_checker
class TrailingWhitespace(BaseChecker):
    def check(self, line):
        """E101 trailing whitespace"""
        line = line.rstrip("\r\n")
        stripped_line = line.rstrip()
        if line != stripped_line:
            return len(stripped_line)

        return None

    def fix(self, line):
        return line.strip() + "\n"


################################################################################
# Framework
################################################################################


class CheckerParameters:
    def __init__(self):
        self._lines = []
        self._next = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._next == self.total_lines:
            raise StopIteration
        else:
            self._next += 1
            return self.lines[self.line_number]

    @property
    def lines(self):
        return self._lines

    @lines.setter
    def lines(self, value):
        self._lines = value
        self._next = 0

    @property
    def line_number(self):
        return self._next - 1

    @property
    def total_lines(self):
        return len(self._lines)

    @property
    def line(self):
        return (self.lines[self.line_number]
                if self.line_number < self.total_lines
                else None)


class Reporter:
    ERROR_CODE_PATTERN = re.compile(r"^[EW]\d+")

    def __init__(self):
        self._filename = None

    def start_file(self, filename):
        self._filename = filename
        print(filename)

    def error(self, line_number, offset, checker):
        error_code = Reporter.ERROR_CODE_PATTERN.match(
            checker.check.__doc__).group(0)
        description = checker.check.__doc__

        print(f"{self._filename}:{line_number}:{offset}: {description}")



class StyleChecker:
    def __init__(self, options):
        self.options = options
        self.extensions = (".src", ".dat", ".sub")

        self._parameters = CheckerParameters()
        self._reporter = Reporter()

    checkers = CHECKERS

    def check(self):
        for target in self.options.target:
            if os.path.isdir(target):
                self._check_directory(target)
            else:
                self._check_file(target)

    def _check_directory(self, dirname):
        for dirpath, _, filenames in os.walk(dirname):
            for filename in sorted(filter(
                    lambda file: file.endswith(self.extensions), filenames)):
                self._check_file(os.path.join(dirpath, filename))

    def _check_file(self, filename):
        self._reporter.start_file(filename)

        with open(filename) as content:
            self._parameters.lines = content.readlines()

        for _ in self._parameters:
            for checker in StyleChecker.checkers:
                self._check_result(self._run_check(checker), checker)

    def _check_result(self, result, checker):
        if result is None:
            return
        self._reporter.error(self._parameters.line_number, result, checker)


    def _run_check(self, checker):
        return self._run_method(checker.check)

    def _run_fix(self, checker):
        return self._run_method(checker.fix)

    def _run_method(self, method):
        parameters = []
        for parameter in _get_parameters(method):
            parameters.append(getattr(self._parameters, parameter))

        return method(*parameters)


def _get_parameters(method):
    return [parameter.name
            for parameter in inspect.signature(method).parameters.values()
            if parameter.kind == parameter.POSITIONAL_OR_KEYWORD]

def _create_arg_parser():
    from argparse import ArgumentParser

    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("target", nargs="*", help="file or folder to check")

    return parser

def _parse_args():
    return _create_arg_parser().parse_args()


def _main():
    style_checker = StyleChecker(_parse_args())
    style_checker.check()


if __name__ == "__main__":
    _main()
