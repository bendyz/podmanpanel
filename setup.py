from setuptools import setup

setup(
    name="podmanpanel",
    version="0.1.0",
    packages=["app", "app.routers"],
    install_requires=[
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.30.0",
        "python-multipart>=0.0.12",
        "bcrypt>=4.0.0",
        "itsdangerous>=2.1.0",
    ],
    entry_points={
        "console_scripts": [
            "podmanpanel=app.main:main",
        ],
    },
    python_requires=">=3.11",
)