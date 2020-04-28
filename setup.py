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
    "Programming Language :: SQL",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: BSD License",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
    "Development Status :: 3 - Alpha",
    "Operating System :: OS Independent",
    "Topic :: Software Development",
    "Topic :: Software Development :: Code Generators",
    "Topic :: Database",
    "Topic :: Database :: Front-Ends",
]

with open("README.md", "r") as fp:
    long_description = fp.read()

setup(name="sqwrl",
      version="0.1.0",
      author="Michael Tartre",
      author_email="michael@enkratic.com",
      url="https://github.com/quantology/sqwrl",
      packages=["sqwrl"],
      install_requires=["pandas", "numpy", "sqlalchemy", "sympy", "toolz", "datashape"],
      description="Sqlachemy Query WRapper Library - pandas-like SQL",
      long_description=long_description,
      long_description_content_type='text/markdown',
      license="bsd-3-clause",
      classifiers=classifiers
      )
