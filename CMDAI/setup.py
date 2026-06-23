from setuptools import setup, find_packages

setup(
    name="cmdai-code",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'cmdai-code=src.main:main',
            'cmdai=src.main:main',
        ],
    },
)
