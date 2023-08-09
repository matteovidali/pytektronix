from distutils.core import setup

setup(
    name='pytektronix',
    packages=['pytektronix'],
    version='0.1',
    license='MIT',
    description='Control your Tektronix Oscilloscopes via python using the VXI11 or pyVISA backend',
    author='Matteo Vidali',
    author_email='mmvidali@gmail.com',
    url=GET,
    download_url=GET,
    keywords = [],
    install_requires=['aenum', 'pyvisa-py', 'vxi11', ''],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

)
