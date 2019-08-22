load("@//3rdparty/python:requirements.bzl", requirement = "requirement")

py_library(
    name = "greeting",
    srcs = glob([
        "greeting.py",
    ]),
    deps = [
        requirement("coolname"),
    ],
)

py_binary(
    name = "greet",
    deps = [":greeting"],
    srcs = ["greet.py"],
)
