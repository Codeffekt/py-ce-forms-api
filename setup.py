from setuptools import setup, find_packages

# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

VERSION = '0.1.11'
DESCRIPTION = 'A Python library for the CeForms API.'

setup(
    name="py_ce_forms_api",
    version=VERSION,
    author='codeffekt',
    author_email='contact@codeffekt.com',
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    install_requires=['requests','fastapi','uvicorn'],
    keywords=['python', 'ceforms', 'api'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',        
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        'Topic :: Software Development',
        'Topic :: Utilities',
        'License :: OSI Approved :: Apache Software License',            
    ],
    entry_points = {
        'console_scripts': ['py-ce-forms=py_ce_forms_api.cli.py_ce_forms:cli'],
    }
)