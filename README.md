# JAF - Juspay AI Framework

**JAF** is python framework for easy building LLM based agents, pipelines, executables and chatbots in Python.  
This framework provides you with the most important subsystems already integrated to build on top of LLMs, such as vector db, document parser, LLM integration, Sematic Routing and other
<br><br>
This framework represents LLM pipeline components as basic building blocks, so you don't have to worry about how to use it.
<br>

- [Installation](#installation)
   -  [Python API](#python-api)
   -  [Development](#setting-up-for-developement)
- [Run Locally with UI](#run-locally-with-ui)
- [Use Python API](#use-python-api)
- [Tutorials](#tutorials)


## Installation
You can use JAF as an application with interative UI or just consume it's python api in your application. Follow below steps to setup JAF.

### Python API
To use JAF's python apis you can run following command to install JAF as python package
```
   $ pip3 install git+https://github.com/juspay/JAF.git
```


### Setting up for developement
clone repo to the local.

1. Create virtual env for python
```
$ python3 -m venv .env
```

2. Activates virtual env
```
$ source .env/bin/activate      
```

3. Install poetry for dependency management
```
$ pip3 install poetry
```

For M1 mac with Rosseta is enabled
```
$ arch -arm64 python -m pip install poetry --no-cache
```
Restart terminal and venv and run command again if you're facing arm46 <> x86 issue.


4. Install all dependencies
```
$ poetry install
```
<br/>


# Tutorials
Tutorials coming soon