from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).parent
readme = (here / "README.md").read_text(encoding="utf-8") if (here / "README.md").exists() else ""

setup(
    name="agi-core",
    version="0.1.0",
    description="Modular AGI service scaffold",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24",
        "pydantic>=1.10",
        "PyYAML>=6.0",
        "psutil>=5.9",
    ],
    extras_require={
        "dev": ["pytest>=7.4"],
        "vector": [
            "chromadb>=0.4.22",
            "psycopg[binary]>=3.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "agi-core=agi_core.app:main",
        ]
    },
    include_package_data=True,
)
