#!/usr/bin/env python3
#
# Copyright 2017 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Modified version of rules_python's wheel tool. Original version:

https://github.com/bazelbuild/rules_python

This version has been modified to support Python3
"""

import email  # for parsing email-style (RFC822) headers
import json
import logging
import os
import re
import sys
import zipfile

import pkg_resources
from pkg_resources._vendor.packaging import markers


logger = logging.getLogger(__name__)


def recurse_split_extra(parsed_parts):
    extra = ""
    remaining = []

    for part in parsed_parts:
        if isinstance(part, list):
            # parenthesized expressions are lists
            sub_extra, sub_remaining = recurse_split_extra(part)
            if sub_extra != "":
                assert extra == ""
                extra = sub_extra
            remaining.append(sub_remaining)
        elif isinstance(part, tuple):
            if isinstance(part[0], markers.Variable) and part[0].value == "extra":
                # Found the extra part: parse it and skip it
                op = part[1]
                value = part[2]
                assert isinstance(op, markers.Op) and op.value == "=="
                assert isinstance(value, markers.Value)
                assert len(value.value) > 0
                assert extra == ""
                extra = value.value

                # if the previous item is now a dangling boolean operator: trim it
                if len(remaining) > 0 and isinstance(remaining[-1], str):
                    remaining = remaining[:-1]
            else:
                remaining.append(part)
        elif isinstance(part, str):
            # must be an operator: just append it
            remaining.append(part)
        else:
            raise Exception("unhandled part: " + repr(part))

    # if the first item is a dangling boolean operator: trim it
    if len(remaining) > 0 and isinstance(remaining[0], str):
        remaining = remaining[1:]
    return extra, remaining


def recurse_str(parsed_parts):
    out = ""
    for part in parsed_parts:
        if isinstance(part, list):
            out += "(" + recurse_str(part) + ")"
        elif isinstance(part, tuple):
            out += " ".join(p.serialize() for p in part)
        elif isinstance(part, str):
            out += " " + part + " "
        else:
            raise Exception("unhandled part: " + repr(part))
    return out


def split_extra_from_environment_marker(environment_marker):
    """
    Splits an environment marker into (extra, remaining environment). It parses the expression,
    then finds the "extra==X" clause. That clause is removed, and the expression is serialized.
    """

    marker = markers.Marker(environment_marker)
    extra, remaining = recurse_split_extra(marker._markers)

    # rebuild the string
    environment_string = recurse_str(remaining)

    return extra, environment_string


class Wheel(object):
    def __init__(self, path):
        self._path = path

    def path(self):
        return self._path

    def basename(self):
        return os.path.basename(self.path())

    def distribution(self):
        # See https://www.python.org/dev/peps/pep-0427/#file-name-convention
        parts = self.basename().split("-")
        return parts[0]

    def version(self):
        # See https://www.python.org/dev/peps/pep-0427/#file-name-convention
        parts = self.basename().split("-")
        return parts[1]

    def repository_name(self):
        # Returns the canonical name of the Bazel repository for this package.
        canonical = "pypi__{}_{}".format(self.distribution(), self.version())
        # Escape any illegal characters with underscore.
        return re.sub("[-.+]", "_", canonical)

    def _dist_info(self):
        # Return the name of the dist-info directory within the .whl file.
        # e.g. google_cloud-0.27.0-py2.py3-none-any.whl ->
        #      google_cloud-0.27.0.dist-info
        return "{}-{}.dist-info".format(self.distribution(), self.version())

    def metadata(self):
        # Extract the structured data from metadata.json in the WHL's dist-info
        # directory.
        with zipfile.ZipFile(self.path(), "r") as whl:
            # first check for metadata.json
            try:
                with whl.open(self._dist_info() + "/metadata.json") as f:
                    return json.loads(f.read().decode("utf-8"))

            except KeyError:
                pass
            # fall back to METADATA file (https://www.python.org/dev/peps/pep-0427/)
            with whl.open(self._dist_info() + "/METADATA") as f:
                return self._parse_metadata(f)

    def name(self):
        return self.metadata().get("name")

    def dependencies(self, extra=None):
        """Access the dependencies of this Wheel.

        Args:
        extra: if specified, include the additional dependencies
                of the named "extra".

        Yields:
        the names of requirements from the metadata.json
        """
        # TODO(mattmoor): Is there a schema to follow for this?
        run_requires = self.metadata().get("run_requires", [])
        for requirement in run_requires:
            if requirement.get("extra") != extra:
                # Match the requirements for the extra we're looking for.
                continue
            marker = requirement.get("environment")
            if marker and not pkg_resources.evaluate_marker(marker):
                # The current environment does not match the provided PEP 508 marker,
                # so ignore this requirement.
                continue
            requires = requirement.get("requires", [])
            for entry in requires:
                # Strip off any trailing versioning data.
                parts = re.split("[ ><=()]", entry)
                package_name = parts[0]
                # For some packages Requires-Dist contains extras defined like:
                # tablib[html,ods,xls,xlsx,yaml] (>=0.14.0)
                # Since we don't support extras, we should remove that part completely,
                # otherwise we end up having `py_library.deps` like `tablib[html,ods,xls,xlsx,yaml]`
                # which isn't a valid bazel dep
                if package_name.endswith(']'):
                    package_name = package_name.split('[')[0]
                yield package_name

    def extras(self):
        return self.metadata().get("extras", [])

    def expand(self, directory):
        with zipfile.ZipFile(self.path(), "r") as whl:
            whl.extractall(directory)

    # _parse_metadata parses METADATA files according to https://www.python.org/dev/peps/pep-0566/
    def _parse_metadata(self, file_object):
        # the METADATA file is in PKG-INFO format, which is a sequence of RFC822 headers:
        # https://www.python.org/dev/peps/pep-0241/
        message = email.message_from_binary_file(file_object)

        # Requires-Dist format:
        # https://packaging.python.org/specifications/core-metadata/#requires-dist-multiple-use
        requires_extra = {}
        extras = set()
        requires = message.get_all("Requires-Dist") or []
        for specification in requires:
            package_and_version = specification
            environment_marker = ""
            extra = ""
            if ";" in specification:
                parts = specification.split(";", 2)
                package_and_version = parts[0].strip()
                environment_marker = parts[1].strip()

                extra, environment_marker = split_extra_from_environment_marker(
                    environment_marker
                )

            if extra != "":
                extras.add(extra)

            key = (extra, environment_marker)
            requires = requires_extra.get(key, [])
            requires.append(package_and_version)
            requires_extra[key] = requires

        run_requires = []

        for (extra, environment_marker), requires in requires_extra.items():
            value = {"requires": requires}
            if extra:
                value["extra"] = extra
            if environment_marker:
                value["environment"] = environment_marker
            run_requires.append(value)

        data = {
            "name": message["Name"],
            "version": message["Version"],
            "run_requires": run_requires,
            "extras": list(extras),
        }
        return data


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: wheeltool.py (input wheel)\n")
        sys.exit(1)
    wheel = Wheel(sys.argv[1])

    extra_deps = {}
    for extra in wheel.extras():
        extra_deps[extra] = list(wheel.dependencies(extra=extra))

    output = dict(requires=list(wheel.dependencies()), extras=extra_deps)
    sys.stdout.write(json.dumps(output) + "\n")


if __name__ == "__main__":
    main()
