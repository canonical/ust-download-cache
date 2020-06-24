import os

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

os.umask(0o022)

setuptools.setup(
    name="UST Download Cache",
    version="1.0.1",
    author="Mike Salvatore <mike.salvatore@canonical.com>",
    description="A package for caching downloads of specially formatted files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/canonical/ust-download-cache",
    packages=setuptools.find_packages(exclude=["tests"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Topic :: Security",
    ],
    install_requires=["pycurl"],
    python_requires=">=3.5",
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest-cov"],
)
