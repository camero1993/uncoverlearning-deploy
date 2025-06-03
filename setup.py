from setuptools import setup, find_packages

setup(
    name="uncoverlearning",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain",
        "langchain-community",
        "langchain-core",
        "langchain-google-genai",
        "supabase",
        "google-cloud-storage",
        "python-dotenv",
        "fastapi",
        "pytest",
    ],
) 