from setuptools import setup, find_packages

setup(
    name="codify",
    version="0.1.0",
    py_modules=["main"] if not find_packages() else find_packages(),
    install_requires=[
        "click",
        "gitpython",
        "litellm",
        "rich",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-mock",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "codify=main:cli",
        ],
    },
)