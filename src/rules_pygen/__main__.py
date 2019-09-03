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
import argparse
import errno
import logging
import os
import shutil
import sys
import tempfile

from rules_pygen.rules_generator import RequirementsToBazelLibGenerator


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bazel Python rules generator.", prog="generator")
    parser.add_argument(
        "requirements-file", action="store", help="Absolute path to the requirements.txt file"
    )
    parser.add_argument(
        "bazel-rules-file",
        action="store",
        help="Absolute path to the file to store Skylark build rules",
    )
    parser.add_argument(
        "bazel-library-path",
        action="store",
        help='Bazel path to the libs. Example: "//3rdparty/python/mylib',
    )
    parser.add_argument(
        "--wheel-dir",
        action="store",
        help="Path to a directory to store wheels. A temporary directory will"
        " be created for you (and removed) if you do not specify this",
    )
    parser.add_argument(
        "--python",
        action="store",
        help='The version of python to use, example: "37"',
        default="37",
    )

    pargs = parser.parse_args()
    args_lookup = vars(pargs)
    reqs_txt = os.path.abspath(args_lookup["requirements-file"])
    bzl_file = os.path.abspath(args_lookup["bazel-rules-file"])
    bzl_path = args_lookup["bazel-library-path"]

    if not bzl_path.startswith("//"):
        sys.stdout.write("Invalid bazel-library-path. Should be like //3rdparty/python/mylib\n")
        sys.exit(1)

    uses_temp = False
    if not pargs.wheel_dir:
        wheel_dir = tempfile.mkdtemp()
        uses_temp = True
    else:
        wheel_dir = os.path.abspath(pargs.wheel_dir)
        try:
            os.makedirs(wheel_dir)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(wheel_dir):
                pass
            else:
                raise

    gen = RequirementsToBazelLibGenerator(reqs_txt, wheel_dir, bzl_file, bzl_path, pargs.python)
    gen.run()
    if uses_temp:
        shutil.rmtree(wheel_dir)
