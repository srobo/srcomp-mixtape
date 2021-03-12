from setuptools import find_packages, setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='sr.comp.mixtape',
    version='1.0.0',
    packages=find_packages(),
    namespace_packages=['sr', 'sr.comp'],
    description='A mixtape for the SR competition.',
    long_description=long_description,
    author='Student Robotics Competition Software SIG',
    author_email='srobo-devel@googlegroups.com',
    install_requires=[
        'requests >=2.5, <3',
        'ruamel.yaml >=0.15, <0.16',
        'sseclient >=0.0, <1',
        'python-dateutil >=2.4, <3',
        'typing-extensions >=3.7.4.3, <4',
    ],
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'srcomp-mixtape = sr.comp.mixtape.cli:main',
        ],
    },
    setup_requires=[
        'Sphinx >=1.3, <2',
    ],
)
