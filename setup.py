try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

classifiers = [
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
    "Development Status :: 3 - Alpha",
    "Operating System :: OS Independent",
    "Topic :: Software Development",
    "Topic :: Software Development :: Code Generators",
    "Topic :: Software Development :: User Interfaces",
    "Topic :: System :: Shells",
]

with open("README.md", "r") as fp:
    long_description = fp.read()

setup(name="sqwrl",
      version="0.0.1",
      author="Michael Tartre",
      author_email="michael@enkratic.com",
      url="https://github.com/enkratic/sqwrl",
      py_modules=["sqwrl"],
      install_requires=["pandas", "numpy", "sqlalchemy", "sympy", "toolz", "datashape"],
      description="Sqlachemy Query WRapper Library - pandas-like SQL",
      long_description=long_description,
      license="MIT",
      classifiers=classifiers
      )
