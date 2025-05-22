from setuptools import setup, find_packages

setup(
    name="space-game",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Abhängigkeiten werden aus requirements.txt gelesen
    ],
    author="",
    author_email="",
    description="Space Game mit Handgestenerkennung und KI-Gegnern",
    keywords="space, game, ai, computer-vision",
    url="",
    project_urls={
        "Source Code": "https://github.com/username/space-game",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 