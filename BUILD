py_binary(
    name = "generator",
    srcs = glob(["src/**/*.py"]),
    main = "src/rules_pygen/__main__.py",
    imports = ["src"],
    legacy_create_init = 0,
    visibility = ["//visibility:public"]
)

py_test(
    name = "generator_tests",
    srcs = glob(["test/**/*.py"]),
    main = "test/rules_pygen/__main__.py",
    deps = [":generator"],
    visibility = ["//visibility:private"]
)
