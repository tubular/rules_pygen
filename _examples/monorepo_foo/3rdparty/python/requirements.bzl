# AUTO GENERATED. DO NOT EDIT DIRECTLY.
#
# Generated with https://github.com/tubular/rules_pygen
#
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

_BUILD_FILE_CONTENT='''

native.py_library(
    name = "pkg",
    srcs = glob(["**/*.py"]),
    data = glob(["**/*"], exclude=[
        "**/*.py", "BUILD", "BUILD.bazel", "WORKSPACE", "*.whl.zip", "**/*.ipynb"
    ]),
    imports = ["."],
    visibility = ["//visibility:public"],
)
'''

def pypi_libraries():

    native.py_library(
        name = "asynctest",
        deps = [
        ] + ["@pypi__asynctest_0_11_1//:pkg"],
        visibility=["//visibility:public"],
    )

    native.py_library(
        name = "coolname",
        deps = [
        ] + ["@pypi__coolname_1_1_0//:pkg"],
        visibility=["//visibility:public"],
    )

    native.py_library(
        name = "freezegun",
        deps = [
            "python_dateutil",
            "six",
        ] + ["@pypi__freezegun_0_3_8//:pkg"],
        visibility=["//visibility:public"],
    )

    native.py_library(
        name = "mock",
        deps = [
            "pbr",
            "six",
        ] + ["@pypi__mock_2_0_0//:pkg"],
        visibility=["//visibility:public"],
    )

    native.py_library(
        name = "pbr",
        deps = [
        ] + ["@pypi__pbr_5_4_2//:pkg"],
        visibility=["//visibility:public"],
    )

    native.py_library(
        name = "py",
        deps = [
        ] + ["@pypi__py_1_8_0//:pkg"],
        visibility=["//visibility:public"],
    )

    native.py_library(
        name = "pytest",
        deps = [
            "py",
        ] + ["@pypi__pytest_2_8_2//:pkg"],
        visibility=["//visibility:public"],
    )

    native.py_library(
        name = "python_dateutil",
        deps = [
            "six",
        ] + ["@pypi__python_dateutil_2_8_0//:pkg"],
        visibility=["//visibility:public"],
    )

    native.py_library(
        name = "six",
        deps = [
        ] + ["@pypi__six_1_12_0//:pkg"],
        visibility=["//visibility:public"],
    )

    native.py_library(
        name = "testfixtures",
        deps = [
        ] + ["@pypi__testfixtures_4_3_3//:pkg"],
        visibility=["//visibility:public"],
    )



def pypi_archives():
    existing_rules = native.existing_rules()
    if "pypi__asynctest_0_11_1" not in existing_rules:
        http_archive(
            name = "pypi__asynctest_0_11_1",
            urls = ["https://files.pythonhosted.org/packages/c1/53/0f862b3a4defe98731326f1aeee743a726001805e17d7688e51bea7cebd3/asynctest-0.11.1-py3-none-any.whl"],
            sha256 = "f47eb8fd1f78a63a68709c2fd471bbde038deffd4e99b8d614b988a8610c09b2",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )

    if "pypi__coolname_1_1_0" not in existing_rules:
        http_archive(
            name = "pypi__coolname_1_1_0",
            urls = ["https://files.pythonhosted.org/packages/25/43/64c0cec51944924f44c0788c329a2c6fde061428c97d7cba73de177ececd/coolname-1.1.0-py2.py3-none-any.whl"],
            sha256 = "e6a83a0ac88640f4f3d2070438dbe112fe80cfebc119c93bd402976ec84c0978",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )

    if "pypi__freezegun_0_3_8" not in existing_rules:
        http_archive(
            name = "pypi__freezegun_0_3_8",
            urls = ["https://files.pythonhosted.org/packages/0f/e9/c7d3ff0a0f1650dae522ac75bd1990c20a6fbf521385a8f6902b5d1f99f4/freezegun-0.3.8-py2.py3-none-any.whl"],
            sha256 = "1557d054523b67732b05bd87bf6e0b551ce648f759cfa05e42c820fdc72d41d8",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )

    if "pypi__mock_2_0_0" not in existing_rules:
        http_archive(
            name = "pypi__mock_2_0_0",
            urls = ["https://files.pythonhosted.org/packages/e6/35/f187bdf23be87092bd0f1200d43d23076cee4d0dec109f195173fd3ebc79/mock-2.0.0-py2.py3-none-any.whl"],
            sha256 = "5ce3c71c5545b472da17b72268978914d0252980348636840bd34a00b5cc96c1",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )

    if "pypi__pbr_5_4_2" not in existing_rules:
        http_archive(
            name = "pypi__pbr_5_4_2",
            urls = ["https://files.pythonhosted.org/packages/f9/d8/bd657bfa0e89eb71ad5e977ed99a9bb2b44e5db68d9190970637c26501bb/pbr-5.4.2-py2.py3-none-any.whl"],
            sha256 = "56e52299170b9492513c64be44736d27a512fa7e606f21942160b68ce510b4bc",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )

    if "pypi__py_1_8_0" not in existing_rules:
        http_archive(
            name = "pypi__py_1_8_0",
            urls = ["https://files.pythonhosted.org/packages/76/bc/394ad449851729244a97857ee14d7cba61ddb268dce3db538ba2f2ba1f0f/py-1.8.0-py2.py3-none-any.whl"],
            sha256 = "64f65755aee5b381cea27766a3a147c3f15b9b6b9ac88676de66ba2ae36793fa",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )

    if "pypi__pytest_2_8_2" not in existing_rules:
        http_archive(
            name = "pypi__pytest_2_8_2",
            urls = ["https://files.pythonhosted.org/packages/08/8b/d6225fbe08f4d5c1b4ff05d274596f76003064dfb3ac6aa483790d1bdd08/pytest-2.8.2-py2.py3-none-any.whl"],
            sha256 = "8699d2ae342f211d1cc67dd05111b91925609aef7d294831584f737f65a4f41d",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )

    if "pypi__python_dateutil_2_8_0" not in existing_rules:
        http_archive(
            name = "pypi__python_dateutil_2_8_0",
            urls = ["https://files.pythonhosted.org/packages/41/17/c62faccbfbd163c7f57f3844689e3a78bae1f403648a6afb1d0866d87fbb/python_dateutil-2.8.0-py2.py3-none-any.whl"],
            sha256 = "7e6584c74aeed623791615e26efd690f29817a27c73085b78e4bad02493df2fb",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )

    if "pypi__six_1_12_0" not in existing_rules:
        http_archive(
            name = "pypi__six_1_12_0",
            urls = ["https://files.pythonhosted.org/packages/73/fb/00a976f728d0d1fecfe898238ce23f502a721c0ac0ecfedb80e0d88c64e9/six-1.12.0-py2.py3-none-any.whl"],
            sha256 = "3350809f0555b11f552448330d0b52d5f24c91a322ea4a15ef22629740f3761c",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )

    if "pypi__testfixtures_4_3_3" not in existing_rules:
        http_archive(
            name = "pypi__testfixtures_4_3_3",
            urls = ["https://files.pythonhosted.org/packages/c7/7d/1288e3a379113971e931097e813de37c257f3638fa9e84ea321a85ceddd1/testfixtures-4.3.3-py2.py3-none-any.whl"],
            sha256 = "42561a34d1f0d18b7c005a1b6d28fc389ee881f80b66d0fa675ed2a7be77bfcf",
            build_file_content = _BUILD_FILE_CONTENT,
            type = "zip",
        )


def requirement(name):
    name_key = name.replace("-", "_").lower()  # allow use of dashes and uppercase
    return "//3rdparty/python:{}".format(name_key)
