import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="placeless-pdb",
    version="0.0.15",
    author="PlaceLess",
    author_email="placeless9@gmail.com",
    description="A DB placeless client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/placeless9/placeless-pdb",
    project_urls={
        "Bug Tracker": "https://github.com/placeless9/placeless-pdb/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
