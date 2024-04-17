from setuptools import setup, find_packages

VERSION = '0.0.5'
DESCRIPTION = 'A Python library for the CeForms API.'

setup(
    name="ce_forms",
    version=VERSION,
    author='codeffekt',
    author_email='contact@codeffekt.com',
    description=DESCRIPTION,
    long_description='',
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
    ]
)