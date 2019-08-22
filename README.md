# rules_pygen
Rules for generating native Bazel Python libraries from a requirements.txt file.

Currently, using pip and a requirements.txt file is the standard for installing dependencies
in a Python project. Unfortunately, Bazel doesn't understand requirements.txt files and only
undestands the concept of a `py_library`; which is one or more Python source files. This library
aims to bridge that gap. The rules_pygen generator takes a requirements.txt file as an input and
generates a dependency graph of `py_library` rules based on the dependencies and subdependencies
that pip would install given that requirements.txt file. In cases where a dependency is 
platform-specific, this tool generates two variants, one for MacOS and another for Linux.

The most common way to use this is in a monorepo where one requirements.txt defines all the 
Python dependencies in your project, though you could potentially have more than one requirements
file. 

## Limitations

* The script itself runs on Python3.5+
* Only works with wheels right now

## Usage & Set up

1. Add a `git_repository` rule to your WORKSPACE file to import the generator:

```
git_repository(
    name = "rules_pygen",
    remote = "https://github.com/tubular/rules_pygen.git",
    commit = "28835b7d278744916890f1ab3d974e7f5d75836c",
)
```

2. Use the generator with local inputs:
```
bazel run @rules_pygen//:generator -- $(pwd)/path/to/python/requirements.txt $(pwd)/path/to/python/requirements.bzl //3rdparty/python --python=37
```

3. Add to your WORKSPACE:

```
load("@//path/to:requirements.bzl", pypi_deps = "pypi_archives")
pypi_deps()
```

4. Use in a BUILD file:

**alternative 1**

```
py_library(
    name = "foo",
    srcs = glob([
        "src/foo/**/*.py",
    ]),
    deps = [
        "//3rdparty/python:pytest",
    ],
)
```

**alternative 2**

```
load("@//3rdparty/python:requirements.bzl", requirement = "requirement")
py_library(
    name = "baz",
    srcs = glob([
        "src/baz/**/*.py",
    ]),
    deps = [
        requirement("pytest"),
    ],
)
```


## Development

### Design choices

* Generated build files should follow Skylark style guide (https://docs.bazel.build/versions/master/skylark/bzl-style.html) as much as possible
* Code should be Python3.5+ compatible
* No external dependencies; this is a library for generating imports we don't to make it hard to use

### Running tests

```
bazel run :generator_tests
```
