from setuptools import setup

version="1.0.0"

with open("README.md", "r") as fd:
    long_description = fd.read()

setup(
    name="leica2tif",
    version=version,
    description="Leica (and possibly other file formats) to TIF",
    long_description=long_description,
    author="Kwanghun Chung Lab",
    packages=["leica2tif"],
    url="https://github.com/chunglabmit/leica2tif",
    license="MIT",
    entry_points={'console_scripts': [
        "leica2tif=leica2tif.main:main"
        ]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        'Programming Language :: Python :: 3.5'
    ],
    install_requires=[
        "bioformats",
        "javabridge",
        "tifffile",
        "tqdm"
    ]
)