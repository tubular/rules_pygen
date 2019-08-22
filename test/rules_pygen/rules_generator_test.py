import operator
import unittest
import unittest.mock


class WhenGeneratingBuildFilesTest(unittest.TestCase):
    def test_that_wheel_compatibility_is_correct(self):
        from rules_pygen.rules_generator import _check_compatibility

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

    def test_that_subdeps_are_correct(self):
        from rules_pygen.rules_generator import DependencyInfo

        di = DependencyInfo('foo', ['Baz', 'bar-Qux', 'QuzQuz'], [])

        self.assertEqual(di.dependencies, ['bar_qux', 'baz', 'quzquz'])
