from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'celegans_sim'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
        (os.path.join('share', package_name, 'urdf'),
            glob('urdf/*')),
        (os.path.join('share', package_name, 'worlds'),
            glob('worlds/*')),
        (os.path.join('share', package_name, 'resource'),
            glob('resource/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='You',
    maintainer_email='you@example.com',
    description='C. elegans autonomous simulation with real connectome data',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'neural_sim_node = celegans_sim.neural_sim_node:main',
            'worm_body_node  = celegans_sim.worm_body_node:main',
            'neural_viz_node = celegans_sim.neural_viz_node:main',
        ],
    },
)
