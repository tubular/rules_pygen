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
import operator
import unittest
import unittest.mock


class WhenGeneratingBuildFilesTest(unittest.TestCase):

    def test_that_log_lines_for_additional_links_works(self):
        """
        We rely on logging from pip to show which wheels exist in the repo, the log line
        is emitted here: https://github.com/pypa/pip/blob/master/src/pip/_internal/index/package_finder.py#L745
        but unfortunately changes from time to time...
        """
        from rules_pygen.rules_generator import WHEEL_LINK_RE
        pip19skip = """Skipping link: none of the wheel's tags match: cp27-none-macosx_10_10_intel: https://pypi.tubularlabs.net/__packages/cffi-0.8.6-cp27-none-macosx_10_10_intel.whl#md5=4ddb6f10863ee4fee8d37ed4be8b8d26 (from https://pypi.tubularlabs.net/cffi/)"""
        pip18skip = """Skipping link https://pypi.tubularlabs.net/__packages/cffi-1.11.5-cp35-cp35m-manylinux1_x86_64.whl#md5=e0c83a8bb0f7a0bd9d58bf9bdf33bbcc (from https://pypi.tubularlabs.net/cffi/); it is not compatible with this Python"""

        https_found = """Found link https://pypi.tubularlabs.net/__packages/aiohttp_admin-0.0.1-py2.py3-none-any.whl#md5=e2ca60e687b17302de3a444bb17fd82b (from https://pypi.tubularlabs.net/aiohttp-admin/), version: 0.0.1"""
        plain_http = """Found link http://pypi.tubularlabs.net/__packages/aiohttp_admin-0.0.1-py2.py3-none-any.whl#md5=e2ca60e687b17302de3a444bb17fd82b (from http://pypi.tubularlabs.net/aiohttp-admin/), version: 0.0.1"""

        self.assertTrue(WHEEL_LINK_RE.search(pip19skip))
        self.assertTrue(WHEEL_LINK_RE.search(pip18skip))

        match = WHEEL_LINK_RE.search(pip19skip)
        self.assertEqual(match.group('link'), 'https://pypi.tubularlabs.net/__packages/cffi-0.8.6-cp27-none-macosx_10_10_intel.whl')

        match = WHEEL_LINK_RE.search(pip18skip)
        self.assertEqual(match.group('link'), 'https://pypi.tubularlabs.net/__packages/cffi-1.11.5-cp35-cp35m-manylinux1_x86_64.whl')

        match = WHEEL_LINK_RE.search(https_found)
        self.assertEqual(match.group('link'), 'https://pypi.tubularlabs.net/__packages/aiohttp_admin-0.0.1-py2.py3-none-any.whl')

        match = WHEEL_LINK_RE.search(plain_http)
        self.assertEqual(match.group('link'), 'http://pypi.tubularlabs.net/__packages/aiohttp_admin-0.0.1-py2.py3-none-any.whl')

    def test_that_wheel_compatibility_is_correct(self):
        from rules_pygen.rules_generator import _check_compatibility

        self.assertTrue(_check_compatibility('pydantic-1.4-py36.py37.py38-none-any.whl', '36'))
        self.assertTrue(_check_compatibility('pydantic-1.4-py36.py37.py38-none-any.whl', '37'))
        self.assertTrue(_check_compatibility('pydantic-1.4-py36.py37.py38-none-any.whl', '38'))

        self.assertTrue(_check_compatibility('pytest-3.2.3-py2.py3-none-any.whl', '37'))
        self.assertTrue(_check_compatibility('pytest_hidecaptured-0.1.2-py3-none-any.whl', '37'))
        self.assertTrue(_check_compatibility('Paste-2.0.3-py34-none-any.whl', '37'))
        self.assertTrue(_check_compatibility('cryptography-2.3.1-cp34-abi3-macosx_10_6_intel.whl', '37'))
        self.assertTrue(_check_compatibility('cryptography-2.3.1-cp34-abi3-manylinux1_x86_64.whl', '37'))

        self.assertFalse(_check_compatibility('cryptography-1.6-cp35-cp35m-linux_x86_64.whl', '37'))
        self.assertFalse(_check_compatibility('cryptography-0.7.1-cp27-none-linux_x86_64.whl', '37'))
        self.assertFalse(_check_compatibility('tornado-5.1.1-cp27-cp27mu-linux_x86_64.whl', '37'))

        self.assertTrue(_check_compatibility('pytest-3.2.3-py2.py3-none-any.whl', '35'))
        self.assertTrue(_check_compatibility('pytest_hidecaptured-0.1.2-py3-none-any.whl', '35'))
        self.assertTrue(_check_compatibility('Paste-2.0.3-py34-none-any.whl', '35'))
        self.assertTrue(_check_compatibility('cryptography-2.3.1-cp34-abi3-macosx_10_6_intel.whl', '35'))
        self.assertTrue(_check_compatibility('cryptography-2.3.1-cp34-abi3-manylinux1_x86_64.whl', '35'))

        self.assertFalse(_check_compatibility('cryptography-1.6-cp37-cp37m-linux_x86_64.whl', '35'))
        self.assertFalse(_check_compatibility('cryptography-0.7.1-cp27-none-linux_x86_64.whl', '35'))
        self.assertFalse(_check_compatibility('tornado-5.1.1-cp27-cp27mu-linux_x86_64.whl', '35'))

    @unittest.mock.patch('rules_pygen.rules_generator._calc_sha256sum')
    def test_that_wheels_can_be_sorted(self, mock_checksum):
        from rules_pygen.rules_generator import WheelInfo

        wi1 = WheelInfo(
            '/path/to/foo-1.4.5-py3-none-linux_x68_64.whl',
            'https://example.org',
            'foo',
            '1.4.5',
        )
        wi2 = WheelInfo(
            '/path/to/foo-1.4.5-py3-none-macosx_10_6_intel.whl',
            'https://example.org',
            'foo',
            '1.4.5',
        )

        wheels = [wi2, wi1]
        # Silly test to make sure (part) of our bzl output is deterministic:w
        wheels.sort(key=operator.attrgetter('platform'))
        self.assertEqual(wheels[0].filename, 'foo-1.4.5-py3-none-linux_x68_64.whl')
        self.assertEqual(wi1.platform, 'linux'),
        self.assertEqual(wi2.platform, 'macos'),

    @unittest.mock.patch('rules_pygen.rules_generator._calc_sha256sum')
    def test_that_we_dont_add_multiple_purelib_wheels(self, mock_checksum):
        from rules_pygen.rules_generator import WheelInfo, DependencyInfo

        di = DependencyInfo('foo', [], [])
        wi1 = WheelInfo(
            '/path/to/foo-1.4.5-py3-none-linux_x68_64.whl', 'https://example.org', 'foo', '1.4.5'
        )
        wi2 = WheelInfo(
            '/path/to/foo-1.4.5-py3-none-macosx_10_6_intel.whl',
            'https://example.org',
            'foo',
            '1.4.5',
        )
        wi3 = WheelInfo(
            '/path/to/foo-1.4.5-py3-none-manylinux1_x86_64.whl',
            'https://example.org',
            'foo',
            '1.4.5',
        )
        wi4 = WheelInfo(
            '/path/to/foo-1.4.5-py3-none-any.whl', 'https://example.org', 'foo', '1.4.5'
        )

        di.add_wheel(wi1)
        self.assertEqual(len(di.wheels), 1)

        di.add_wheel(wi2)
        self.assertEqual(len(di.wheels), 2)
        self.assertEqual(
            [w.filename for w in di.wheels],
            ['foo-1.4.5-py3-none-linux_x68_64.whl', 'foo-1.4.5-py3-none-macosx_10_6_intel.whl']
        )

        di.add_wheel(wi3)  # should be ignored because we already have that platform
        self.assertEqual(len(di.wheels), 2)
        self.assertEqual(
            [w.filename for w in di.wheels],
            ['foo-1.4.5-py3-none-linux_x68_64.whl', 'foo-1.4.5-py3-none-macosx_10_6_intel.whl']
        )

        pure_di = DependencyInfo('foo', [], [])
        pure_di.add_wheel(wi4)
        # should be ignored as we consider this a "purelib" wheel where the first will do
        pure_di.add_wheel(wi3)
        self.assertEqual(len(pure_di.wheels), 1)

        pure_di = DependencyInfo('foo', [], [])
        pure_di.add_wheel(wi3)
        pure_di.add_wheel(wi4)  # should remove the first one, purelib takes precedence
        self.assertEqual(len(pure_di.wheels), 1)
        self.assertEqual(pure_di.wheels, [wi4])

    @unittest.mock.patch('rules_pygen.rules_generator._calc_sha256sum')
    def test_that_we_dont_add_multiple_purelib_wheels2(self, mock_checksum):
        from rules_pygen.rules_generator import WheelInfo, DependencyInfo

        di = DependencyInfo('aiohttp-admin', [], [])
        wi1 = WheelInfo(
            '/path/to/aiohttp_admin-0.0.1-py3-none-any.whl', 'https://example.org', 'aiohttp-admin', '0.0.1'
        )
        wi2 = WheelInfo(
            '/path/to/aiohttp_admin-0.0.1-py2.py3-none-any.whl', 'https://example.org', 'aiohttp-admin', '0.0.1'
        )

        di.add_wheel(wi1)
        self.assertEqual(len(di.wheels), 1)

        di.add_wheel(wi2)
        self.assertEqual(len(di.wheels), 1)

    def test_that_subdeps_are_correct(self):
        from rules_pygen.rules_generator import DependencyInfo

        di = DependencyInfo('foo', ['Baz', 'bar-Qux', 'QuzQuz'], [])

        self.assertEqual(di.dependencies, ['bar_qux', 'baz', 'quzquz'])
