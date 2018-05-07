from setuptools import setup, find_packages
setup(
    name='PDS_Pipelines',
    version='1.0.0',
    description='Planetary Data Science processing tools',

    url='https://github.com/USGS-Astrogeology/PDS-Pipelines',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    project_urls={  # Optional
        'Source': 'https://github.com/USGS-Astrogeology/PDS-Pipelines'
    },
)
