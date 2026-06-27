from pathlib import Path

from setuptools import setup, find_packages


requirements = [
    line.strip()
    for line in Path("requirements.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
]

setup(
    name="cmdai-code",
    version="1.0.0",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'cmdai-code=src.main:main',
            'cmdai=src.main:main',
        ],
    },
)
