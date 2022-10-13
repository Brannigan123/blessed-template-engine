from setuptools import setup, find_packages

VERSION = '0.0.1'
DESCRIPTION = 'Package for templates using b_theme'
LONG_DESCRIPTION = 'Package for templates using b_theme'

packages = find_packages()
package_data = {package: ["py.typed"] for package in packages}


setup(
    name="b_theme_template",
    version=VERSION,
    author="Brannigan Sakwah",
    author_email="brannigansakwah@gmail.com",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=packages,
    package_data=package_data,
    entry_points={
        'console_scripts': [
            'update_b_theme = b_theme_template.templates:main'
        ]
    },
    install_requires=[
        'b_theme',
        'jinja2',
        'dataclass_wizard'
    ],
    keywords=['python', 'theme', 'qtile', 'config', 'template', 'dynamic'],
)
