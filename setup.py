"""Setup script for the stoppls package."""

from setuptools import find_packages, setup

setup(
    name="stoppls",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "google-api-python-client",
        "google-auth-oauthlib",
        "anthropic",
        "pyyaml",
    ],
    python_requires=">=3.8",
    author="Christopher DeCarolis",
    description="A Python-based tool to monitor emails and take automated actions",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS",
    ],
    entry_points={
        "console_scripts": [
            "stoppls=stoppls.cli:main",
        ],
    },
)
