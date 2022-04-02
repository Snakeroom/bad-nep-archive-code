# coding=utf-8
from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = f.read().strip().splitlines()

tests_require = ["pytest", "pytest-xdist", "pytest-asyncio"]

setup(
    name="placedump",
    packages=find_packages(),
    install_requires=install_requires,
    tests_require=tests_require,
    zip_safe=False,
)
