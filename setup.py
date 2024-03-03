"""This is a legacy configration file used for defining a package."""

from pathlib import Path

from setuptools import find_packages, setup

from versions import VERSION

with Path("README.md").open(encoding="utf-8") as file:
    description = file.read()

with Path("requirements.txt").open(encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="SongBeamerQS",
    version=VERSION,
    author="bensteUEM",
    author_email="benedict.stein@gmail.com",
    description="A python package with tools improving the quality of Songbeamer files",
    long_description=description,
    long_description_content_type="text/markdown",
    url="https://github.com/bensteUEM/SongBeamerQS",
    license="CC-BY-SA",
    python_requires=">=3.10",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
)
