import setuptools
import os


def get_description():
    if os.path.isfile("README.md"):
        with open("README.md", "r") as fh:
            desc = fh.read()
    else:
        desc = ""
    return desc


setuptools.setup(
    name="ktblame",
    version="0.0.1",
    description="Fine-grained git blame tracking custom key-values over time.",
    long_description=get_description(),
    long_description_content_type="text/markdown",
    author="Haochuan Wei",
    author_email="haochuanwei@yahoo.com",
    url="https://github.com/haochuanwei/ktblame",
    packages=setuptools.find_packages(include=["ktblame*"]),
    install_requires=[
        "gitpython",
        "pydantic",
        "streamlit",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
