#!/usr/bin/env python3
#
# Copyright 2019 Tubular Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
This is intended to read `requirements` from requirements.txt file,
download the wheel for each requirement via pip, pip gets us the wheels in
a directory `wheel_dir` as well as subdependency wheels. We then parse each
wheel for dependencies (this uses wheeltool.py). Then with the dependencies
we create `output_file` which can be called from the WORKSPACE.

TODO:
* What about 'extras'? Extras are essentially alternative versions of the original
library that contain additional dependencies:
     foo = requires {'bar'},           ==> py_library('foo', deps = ['bar'])
     foo[baz] = requires {'baz'}       ==> py_library('foo__baz', deps = ['bar', 'baz'])
--> For now this generator *does not* contain support for extras.
"""

import glob
import hashlib
import logging
import operator
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import typing
import urllib.request

from rules_pygen.wheeltool import Wheel

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


HEADER = """# AUTO GENERATED. DO NOT EDIT DIRECTLY.
#
# Generated with https://github.com/tubular/rules_pygen
#
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

_BUILD_FILE_CONTENT='''

native.py_library(
    name = "pkg",
    srcs = glob(["**/*.py"]),
    data = glob(["**/*"], exclude=[
        "**/*.py", "BUILD", "BUILD.bazel", "WORKSPACE", "*.whl.zip", "**/*.ipynb"
    ]),
    imports = ["."],
    visibility = ["//visibility:public"],
)
'''
"""

FOOTER = """

def requirement(name):
    name_key = name.replace("-", "_").lower()  # allow use of dashes and uppercase
    return "{}:{{}}".format(name_key)
"""

# this matches *.whl files in log lines, note that PyPI can also contain
# tar.gz files (not everything is a wheel) and so this script should deal
# with those as well
WHEEL_LINK_RE = re.compile(r"^\s*(Found|Skipping) link.*(?P<link>https?:[^ #]+\.whl)")

WHEEL_FILENAME_RE = re.compile(r"^.*/(?P<filename>[^\/]*.whl)$")

WHEEL_FILE_RE = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<ver>\d.*?))
    ((-(?P<build>\d.*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
    \.whl|\.dist-info)$""",
    re.VERBOSE,
)

ARCHIVE_TMPL = """
    if "{archive_name}" not in existing_rules:
        http_archive(
            name = "{archive_name}",
            urls = ["{url}"],
            sha256 = "{sha256}",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )
"""

BLACKLIST = {"setuptools", "typing"}  # causes issues in python versions > 3.4

SUPPORTED_PYTHON3_VERSIONS = ["py3", "py2.py3", "py34", "py35", "py36", "py37", "py38"]
CPYTHON_VERSIONS = ("cp34", "cp35", "cp36", "cp37", "cp38")


class PyBazelRuleGeneratorException(Exception):
    pass


def _space(x: int):
    return " " * x


def _download(url: str, dest: str) -> None:
    logger.info("Downloading %s", url)
    urllib.request.urlretrieve(url, dest)


def _calc_sha256sum(filepath: str) -> str:
    with open(filepath, "rb") as fd:
        digest = hashlib.sha256()
        while True:
            buf = fd.read(4096)
            if not buf:
                break
            digest.update(buf)
        return digest.hexdigest()


def _check_compatibility(filename: str, desired_pyver: str) -> bool:
    match = WHEEL_FILE_RE.search(filename)

    if match:
        pyver = match.group("pyver")
        abi = match.group("abi")
    else:
        raise PyBazelRuleGeneratorException(
            "Could not get Python version information from wheel file: {}".format(
                filename
            )
        )

    supported_abis = [
        "abi3",
        "cp{}m".format(desired_pyver),
        "cp{}mu".format(desired_pyver),
    ]
    always_supported_pyvers = [
        "cp{}".format(desired_pyver),
        "py{}".format(desired_pyver),
    ]

    if abi == "none" and pyver in SUPPORTED_PYTHON3_VERSIONS:
        return True
    elif abi in supported_abis and pyver in CPYTHON_VERSIONS:
        return True
    elif pyver in always_supported_pyvers:
        return True
    else:
        logger.info("Skipping, version: %s, abi: %s", pyver, abi)
    return False


class WheelInfo:
    """Struct for information on a wheel."""

    def __init__(self, filepath, url, name, version):
        self.filepath = filepath
        self.url = url
        self.name = name.lower()
        self.version = version

        self.sha256sum = _calc_sha256sum(filepath)
        self.filename = os.path.basename(filepath)

    def __repr__(self):
        return "<{} ({})>".format(self.filename, self.platform)

    @property
    def platform(self) -> str:
        if "linux" in self.filename:
            return "linux"
        elif "macos" in self.filename:
            return "macos"
        return "purelib"

    def __eq__(self, other):
        return isinstance(other, WheelInfo) and (self.filename == other.filename)

    def __hash__(self):
        return hash(self.filename)

    @property
    def archive_name(self) -> str:
        """Name of the archive

        Example: 'pypi__futures_3_1_1'

        This includes the version so that Bazel graph shows it.

        The naming convention matches:
            https://github.com/bazelbuild/rules_python#canonical-whl_library-naming
        """
        version_label = self.version.replace(".", "_")
        if self.platform != "purelib":
            return "pypi__{}_{}__{}".format(self.name, version_label, self.platform)
        return "pypi__{}_{}".format(self.name, version_label)

    @property
    def lib_path(self) -> str:
        """Path of the lib inside the archive

        Example: '@pypi__futures_3_1_1//:pkg
        """
        return "@{}//:pkg".format(self.archive_name)


class DependencyInfo:
    """Struct for information on a dependency.

    A dependency can have 1 or 2 wheels. If it's a "purelib"
    dependency it should have 1 wheel and if it's a "platform"
    dependency it should have 2 wheels, one for linux one for macos
    """

    def __init__(self, name, deps, extras):
        self.name = name.replace("-", "_").lower()
        self._deps = deps  # subdependencies
        self._extras = (
            extras
        )  # TODO(c4urself): implement, don't care about it right now

        self.wheels = []

    @property
    def dependencies(self):
        return sorted([dep.replace("-", "_").lower() for dep in self._deps])

    def verify(self, platforms: typing.Set) -> bool:
        """Verify that this dependency has the necessary wheels."""
        if len(self.wheels) == 1:  # add_wheel ensures only one purelib
            if self.wheels[0].platform == "purelib":
                return True
        existing_platforms = {w.platform for w in self.wheels}
        if platforms == existing_platforms:
            return True
        else:
            logger.error(
                'Verification shows missing platform(s): %s', platforms - existing_platforms
            )
            return False

    def add_wheel(self, wheel: WheelInfo) -> None:
        if self.wheels:
            existing_platforms = {w.platform for w in self.wheels}
            if "purelib" in existing_platforms:
                logger.info("Not adding any more wheels, purelib library")
                return
            elif wheel.platform in existing_platforms:
                logger.info(
                    "Not adding an alternative for platform: %s", wheel.platform
                )
                return
            elif wheel.platform == "purelib":
                logger.info(
                    "Removing existing platform wheels, preferring a purelib variant."
                )
                # weird edge case: we found a wheel that has both platform-specific and
                # purelib variants, let's prefer the purelib wheel
                self.wheels = []
        self.wheels.append(wheel)

    def __eq__(self, other):
        return isinstance(other, DependencyInfo) and (self.name == other.name)

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name


class RequirementsToBazelLibGenerator:
    """Generator for creating Bazel rules from a requirements-file"""

    def __init__(
        self,
        requirements_path: str,
        wheel_dir: str,
        output_file: str,
        bzl_path: str,
        desired_python: str,
    ):
        self.requirements_path = requirements_path
        self.wheel_dir = wheel_dir
        self.output_file = output_file
        self.bzl_path = bzl_path
        self.desired_python = desired_python
        self.desired_python_full = "python{}".format(".".join(self.desired_python))

    def run(self) -> None:
        """Main entrypoint into builder."""
        logger.info("Validating")
        self._validate()
        logger.info("Getting wheel links via pip")
        wheel_links = self._get_wheel_links()
        logger.info("\nParsing dependencies from wheels\n")
        deps = self._parse_wheel_dependencies(wheel_links)
        logger.info("\nGenerating output file\n")
        self._gen_output_file(deps)

    def _validate(self) -> None:
        with open(self.requirements_path, "rt") as f:
            if "--use-wheel\n" in f.readlines():
                raise PyBazelRuleGeneratorException(
                    "Requirements.txt may not contain --use-wheel"
                )
        whl_path = pathlib.Path(self.wheel_dir)

        if not whl_path.parent.exists():
            raise PyBazelRuleGeneratorException(
                "Wheel dir parent directory '{}' does not exist".format(whl_path.parent)
            )

        output_path = pathlib.Path(self.output_file)
        if not output_path.parent.exists():
            raise PyBazelRuleGeneratorException(
                "Output path parent directory '{}' does not exist".format(
                    output_path.parent
                )
            )

    def _get_wheelname_from_link(self, wheel_link: str) -> str:
        """Give a wheel url, return the filename.

        >>> _get_wheelname_from_link('https://foo/__packages/idna_ssl-1.1.0-py3-none-any.whl')
        "idna_ssl-1.1.0-py3-none-any.whl"
        """
        logger.debug("getting filename for %s", wheel_link)
        match = WHEEL_FILENAME_RE.search(wheel_link)
        if match:
            return match.group("filename")
        else:
            return ""

    def _get_wheel_links(self) -> dict:
        wheel_links = {}
        logger.info("Calling pip wheel on: %s", self.requirements_path)
        start = time.time()
        proc = subprocess.Popen(
            shlex.split(
                "{} -m pip wheel --verbose --disable-pip-version-check "
                "--requirement {} --wheel-dir {}".format(
                    self.desired_python_full, self.requirements_path, self.wheel_dir
                )
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        out, err = proc.communicate()
        if proc.returncode != 0:
            raise PyBazelRuleGeneratorException(
                "Pip call caused an error: {}".format(err)
            )
        for line in out.splitlines():
            match = WHEEL_LINK_RE.search(line)
            if match:
                # get filename from link and then add to a lookup dict
                # to store the location of the http links for wheels
                link = match.group("link")
                filename = self._get_wheelname_from_link(link)
                logger.debug("Found link: %s for: %s", link, filename)
                wheel_links[filename] = link
        end = time.time()
        logger.info("pip executed in %s seconds", (end - start) * 1000.0)
        logger.debug("found: %r", wheel_links)
        return wheel_links

    def _parse_wheel_dependencies(self, wheel_links: str) -> typing.Set[DependencyInfo]:
        """Parse wheel dependencies

        Build a set of dependency structs and the wheels that correspond
        with them.

        1. For each wheel that pip downloaded, create a DependencyInfo
        struct and add the wheel to it
        2. Then find any additional wheels that belong to that dependency
        for other platforms

        NOTE: wheel_links contains all kinds of wheels that pip found, part
        of those links aren't useful to use because they're not the right
        version/platform combination.
        """

        all_deps = set([])  # type: DependencyInfo

        # at this point pip has installed all deps+subdeps inside our
        # wheel_dir, even though we're dealing with wheel files, we are
        # really iterating through our full dependency set
        for wheel_filepath in glob.glob("{}/*.whl".format(self.wheel_dir)):
            logger.info("\nProcessing wheelinfo for %s", wheel_filepath)
            wheel = Wheel(wheel_filepath)
            extra_deps = {}
            for extra in wheel.extras():
                extra_deps[extra] = list(wheel.dependencies(extra=extra))

            logger.debug("Wheel name is: %s", wheel.name())
            dependency = DependencyInfo(
                name=wheel.name(),
                deps=set(wheel.dependencies()) - BLACKLIST,
                extras=extra_deps,
            )

            wheel_filename = os.path.basename(wheel_filepath)

            # now we're going to try to find additional wheels for the same
            # library+version on other platforms based on the wheel links
            # that we got from the pip call
            match = WHEEL_FILE_RE.search(wheel_filename)
            if match:
                name, version = match.group("name"), match.group("ver")
                match_prefix = "{}-{}".format(name, version)
            else:
                raise PyBazelRuleGeneratorException("Could not parse wheel file name.")
            logger.debug(
                "Will find additional wheels for other platforms using prefix: %s",
                match_prefix,
            )
            for additional_filename, additional_link in wheel_links.items():
                if additional_filename.startswith(match_prefix):
                    # we've found a wheel with the same name+version, obviously
                    # it could just be the wheel we downloaded (the local wheel)
                    # so we check for that first.
                    logger.info("Found additional wheel: %s", additional_filename)

                    is_compatible = _check_compatibility(
                        additional_filename, self.desired_python
                    )
                    if not is_compatible:
                        continue

                    filepath = os.path.abspath(
                        os.path.join(self.wheel_dir, additional_filename)
                    )
                    logger.debug("Considering %s", additional_filename)

                    if wheel_filename != additional_filename:
                        logger.debug(
                            "%s does not equal %s", wheel_filename, additional_filename
                        )
                        _download(additional_link, filepath)

                    logger.debug("Matched %s %s", match_prefix, additional_filename)

                    wi = WheelInfo(
                        name=name,
                        filepath=filepath,
                        url=additional_link,
                        version=version,
                    )

                    dependency.add_wheel(wi)

            if dependency.name not in BLACKLIST:
                if not dependency.verify({"macos", "linux"}):
                    raise PyBazelRuleGeneratorException(
                        "Dependency {} is missing wheels!".format(dependency)
                    )
                all_deps.add(dependency)
        return all_deps

    def _gen_output_file(self, deps) -> None:
        """Output a file with the following structure

        def pypi_libraries():
            py_library(
                name="virtualenv",
                deps=[
                ] + ["@pypi_virtualenv//:pkg"],
                licenses=["notice"],
                visibility=["//visibility:public"],
            )

        def pypi_archives():
            existing_rules = native.existing_rules()
            if "pypi_asn1crypto" not in existing_rules:
                http_archive(
                    name="pypi_asn1crypto",
                    url="https://files.pythonhosted...",
                    sha256="2f1adbb7546ed199e3c90ef23ec95c5cf3585bac7d11fb7eb562a3fe89c64e87",
                    build_file_content=_BUILD_FILE_CONTENT,
                    type="zip",
                )
        """
        f = tempfile.NamedTemporaryFile(delete=False, mode="w+t")
        # sort the deps for better diffs
        sorted_deps = list(deps)
        sorted_deps.sort(key=operator.attrgetter("name"))

        # header
        f.write(HEADER)
        f.write("\ndef pypi_libraries():\n\n")

        # py_libraries
        for dependency in sorted_deps:
            logger.debug("Writing py_library for %s", dependency)
            f.write(_space(4) + "native.py_library(\n")
            f.write(_space(8) + 'name = "{}",\n'.format(dependency.name))
            f.write(_space(8) + "deps = [\n")
            for subdependency in dependency.dependencies:
                f.write(_space(12) + '"{}",\n'.format(subdependency))
            f.write(_space(8) + "]")
            logger.debug("Found %r dependency wheels", dependency.wheels)
            if len(dependency.wheels) == 0:
                # TODO(c4urself): weird case, investigate
                raise PyBazelRuleGeneratorException(
                    "No wheels for dependency: {}".format(dependency)
                )
            if len(dependency.wheels) == 1:
                # one platform-less/purelib wheel exists
                f.write(' + ["{}"],\n'.format(dependency.wheels[0].lib_path))
            else:
                # multiple platform/platlib wheels exist
                f.write(" + select({\n")
                sorted_wheels = dependency.wheels
                sorted_wheels.sort(key=operator.attrgetter("platform"))
                for wheel in sorted_wheels:
                    if wheel.platform == "linux":
                        f.write(
                            _space(12)
                            + '"@//tool_bazel:linux": ["{}"],\n'.format(wheel.lib_path)
                        )
                    elif wheel.platform == "macos":
                        f.write(
                            _space(12)
                            + '"@//tool_bazel:macos": ["{}"],\n'.format(wheel.lib_path)
                        )
                f.write(_space(8) + "}),\n")
            f.write(_space(8) + 'visibility=["//visibility:public"],\n')
            f.write(_space(4) + ")\n\n")

        f.write("\n\ndef pypi_archives():\n")
        f.write(_space(4) + "existing_rules = native.existing_rules()")

        # archives
        for dependency in sorted_deps:
            sorted_wheels = dependency.wheels
            sorted_wheels.sort(key=operator.attrgetter("platform"))
            for wheel in sorted_wheels:
                f.write(
                    ARCHIVE_TMPL.format(
                        archive_name=wheel.archive_name,
                        url=wheel.url,
                        sha256=wheel.sha256sum,
                    )
                )

        # footer
        f.write(FOOTER.format(self.bzl_path))
        logger.info("Finished writing to output file: %s", self.output_file)
        f.close()
        shutil.copy(f.name, self.output_file)
        os.remove(f.name)
