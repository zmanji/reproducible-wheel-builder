This repo contains a script to reproducibly build Python wheels using PyPA's `build` tool.

The problem is that in the PEP 517/518 world a `pyproject.toml` can have the following entries

````
[build-system]
requires = ["setuptools", "wheel"]
````

The `requires` entries are abstract dependencies and are not pinned to a specific version. Therefore when using `pip` or `build` to build a wheel from a sdist these dependencies are resolved every time. This process is not reproducible and can result in issues if the dependencies have changed behaviour that breaks the build.

To fix this this project combines `pex` with `build` to reproducibly build wheels. This project takes in a pex lockfile which is used when resolving the `requires`. `pex` is then used to create a virtual environment which these dependencies and this virtual environment is passed to `build` which uses that environment for initiating the build itself. This process ensures the build occurs in a reproducible environment every time.


Example
```
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
pex --lock pex.lock --exe main.py --python-shebang '/usr/bin/env python3' --include-tools -o main.pex
```

This should build a pex that works on Python 3.7+

### Venv for development
After building `main.pex` create a venv by running:
```
PEX_TOOLS=1 ./main.pex venv -b prepend --rm pex -f ./venv
```