import glob

for filename in glob.glob('*.py'):
    exec 'from %s import *' % filename[:-3]

if __name__ == '__main__':
    import unittest
    unittest.main()
