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
import logging
import os
import unittest


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.getcwd())
    suite = loader.discover(start_dir, pattern="*test.py")
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
