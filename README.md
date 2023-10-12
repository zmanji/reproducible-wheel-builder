This repo contains a script to reproducibly build Python wheels using PyPA's [`build`](https://github.com/pypa/build) tool and [`pex`](https://github.com/pantsbuild/pex).

## Problem
The problem is that in the PEP 517/518 world a `pyproject.toml` can have the following entries

````
[build-system]
requires = ["setuptools", "wheel"]
````

The `requires` entries are abstract dependencies and are not pinned to a specific version. Therefore when using `pip` or `build` to build a wheel from a sdist these dependencies are resolved every time. This process is not reproducible and can result in issues if the dependencies have changed behaviour that breaks the build. If a project does not have a `pyproject.toml` then the default is `setuptools >= 40.8.0` and `wheel`.

To fix this this project combines `pex` with `build` to reproducibly build wheels. This project takes in a pex lockfile which is used when resolving the `requires`. `pex` is then used to create a virtual environment which these dependencies and this virtual environment is passed to `build` which uses that environment for initiating the build itself. This process ensures the build occurs in a reproducible environment every time. For more information on why using a lockfile is valuable see [Semantic Versioning Will Not Save You](https://hynek.me/articles/semver-will-not-save-you/). 


## Example
This example shows how to build the [pyzstd](https://github.com/animalize/pyzstd) v1.5.3 project in a reproducible environment. This project does not have a `pyproject.toml` so the default is to get an unspecified version of `setuptools`. In our case we want to pass arguments to the existing `setup.py`, so we need at least `setuptools` [64](https://setuptools.pypa.io/en/latest/history.html#v64-0-0) which supports passing build options via a `--build-option` flag.

First grab the `pyzstd` sdist and unpack it somewhere.
```shell
$ wget https://files.pythonhosted.org/packages/12/38/2d56ffd3f6e6d0e982ccb9e9fad4dac6626253bbad714aa0d74c66c0eb46/pyzstd-0.15.3.tar.gz
$ tar xvzf pyzstd-0.15.3.tar.gz
$ rm pyzstd-0.15.3.tar.gz
```

Next create a pex lock file with the desired dependencies. For this build I think it would be best to use `setuptools==64.0.3` and `wheel==0.38.4`.
``` shell
$ cat requirements.in
setuptools==64.0.3
wheel==0.38.4
$ pex3 lock create --resolver-version pip-2020-resolver --pip-version 22.3 --no-build  -r requirements.in --indent 2 --output setuptools.lock
```
The resulting `setupools.lock` file specifies the build environment.

The `setuptools.lock` can be used like so:
```
$ main.pex --lock setuptools.lock --src ./pyzstd-0.15.3 --out ./out --dist wheel --quiet
```
The last printed out line is the built wheel.

Environment variables are passed to the underlying build tool, so for `setuptools` `CLFAGS` and `SOURCE_DATE_EPOCH` can be specified if needed.

``` shell
$ CFLAGS="-march=x86-64-v3 -O3" SOURCE_DATE_EPOCH=0 main.pex --lock setuptools.lock --src ./pyzstd-0.15.3 --out ./out --dist wheel --quiet
```

The `--requires_config` and `--build_config` flags populate the configuration for the build tool. The flags expect a json file which contains a map. The map is passed to the underlying build tool. In the setuptools case we can specify a `--build-option` key with an array of strings value that is passed to the `setup.py` invocation. For `pyzstd` passing `--dynamic-link-zstd` means the resulting wheel will be dynamically linked against the system zstd.

``` shell
$ main.pex --lock setuptools.lock --src ./pyzstd-0.15.3 --out ./out --dist wheel --quiet --build_config <(echo '{"--build-option": ["--dynamic-link-zstd"]}') --requires_config <(echo '{"--build-option": ["--dynamic-link-zstd"]}')
```

The same python that is used to run the script is used to build the wheel, by default it's the first `python3` on the PATH but that can be changed with `PEX_PYTHON`. This can be handy for building the same wheel but with different Pythons. 

``` shell
PEX_PYTHON=~/.pyenv/versions/3.9.13/bin/python3.9 main.pex --lock setuptools.lock --src ./pyzstd-0.15.3 --out ./out --dist wheel --quiet
```
## Development Notes
### Dependencies
To update the version of pex or build edit `requirements.in` then produce a new lockfile by running:
```
env PEX_SCRIPT=pex3 pex lock create --resolver-version pip-2020-resolver --pip-version 22.3 --no-build  -r requirements.in --indent 2 --output pex.lock
```

### Building the binary
To build the final binary from the lockfile and `main.py` run:
```
pex --lock pex.lock --exe main.py --python-shebang '/usr/bin/env python3' --include-tools -o main.pex --platform manylinux2014_x86_64-cp-312-cp312 --platform manylinux2014_x86_64-cp-311-cp311 --platform manylinux2014_x86_64-cp-310-cp310
```

This should build a pex that works on Python 3.10+

### Venv for development
After building `main.pex` create a venv by running:
```
PEX_TOOLS=1 ./main.pex venv -b prepend --rm pex -f ./venv
```
