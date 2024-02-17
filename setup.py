from setuptools import setup, find_packages
from versions import VERSION

with open("README.md", "r") as file:
    description = file.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='SongBeamerQS',
    version=VERSION,
    author='bensteUEM',
    author_email='benedict.stein@gmail.com',
    description='A python package with tools improving the quality of Songbeamer files',
    long_description=description,
    long_description_content_type="text/markdown",
    url='https://github.com/bensteUEM/SongBeamerQS',
    license='CC-BY-SA',
    python_requires='>=3.10',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
)