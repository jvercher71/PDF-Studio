from setuptools import setup, find_packages

setup(
    name='PDFStudio',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'PySide6>=6.5.0',
        'PyMuPDF>=1.23.0',
        'pypdf>=3.0.0',
        'pyHanko>=0.21.0',
        'pyhanko-certvalidator>=0.26.0',
        'cryptography>=41.0.0',
        'Pillow>=10.0.0',
    ],
    python_requires='>=3.10',
)
