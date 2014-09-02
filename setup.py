from setuptools import setup, find_packages

setup(
    name='telemetryserver',
    version='0.0.1',
    description='Telemetry Server',
    packages=find_packages(),
    install_requires=['boto', 'lz4', 'ujson'],
)
