"""Setup configuration for Agentic DevOps Copilot."""
from setuptools import setup, find_packages

setup(
    name="agentic-devops-copilot",
    version="1.0.0",
    author="Chennoji Rajashekar",
    description="AI-powered multi-agent system for automating incident response on Azure",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        line.strip()
        for line in open("requirements.txt").readlines()
        if line.strip() and not line.startswith("#")
    ],
    entry_points={
        "console_scripts": [
            "agentic-devops=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)
