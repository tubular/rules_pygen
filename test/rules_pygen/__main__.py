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
