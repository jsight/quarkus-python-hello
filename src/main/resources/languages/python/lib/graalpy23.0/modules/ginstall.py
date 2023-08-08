# Copyright (c) 2019, 2023, Oracle and/or its affiliates. All rights reserved.
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
#
# The Universal Permissive License (UPL), Version 1.0
#
# Subject to the condition set forth below, permission is hereby granted to any
# person obtaining a copy of this software, associated documentation and/or
# data (collectively the "Software"), free of charge and under any and all
# copyright rights in the Software, and any and all patent rights owned or
# freely licensable by each licensor hereunder covering either (i) the
# unmodified Software as contributed to or provided by such licensor, or (ii)
# the Larger Works (as defined below), to deal in both
#
# (a) the Software, and
#
# (b) any piece of software and/or hardware listed in the lrgrwrks.txt file if
# one is included with the Software each a "Larger Work" to which the Software
# is contributed by such licensors),
#
# without restriction, including without limitation the rights to copy, create
# derivative works of, display, perform, and distribute the Software and make,
# use, sell, offer for sale, import, export, have made, and have sold the
# Software and the Larger Work(s), and to sublicense the foregoing rights on
# either these or other terms.
#
# This license is subject to the following condition:
#
# The above copyright notice and either this complete permission notice or at a
# minimum a reference to the UPL must be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import re
from pathlib import Path
import argparse
import json
import os
import shutil
import site
import subprocess
import tempfile
import importlib
import time

import sys

WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'


def info(msg, *args, **kwargs):
    print(BOLD + msg.format(*args, **kwargs) + ENDC)


def error(msg, *args, **kwargs):
    message = msg.format(*args, **kwargs) if args or kwargs else msg
    print(FAIL + message + ENDC)


def warn(msg, *args, **kwargs):
    message = msg.format(*args, **kwargs) if args or kwargs else msg
    print(WARNING + message + ENDC)


def get_module_name(package_name):
    non_standard_packages = {
        'pyyaml': 'pyaml',
        'protobuf': 'google.protobuf',
        'python-dateutil': 'dateutil',
        'websocket-client': 'websocket',
        'attrs': 'attr',
        'scikit-learn': 'sklearn',
        'scikit_learn': 'sklearn',
    }
    module_name = non_standard_packages.get(package_name, package_name)
    return module_name.replace('-', '_')


def have_flang_new():
    env_path = os.environ.get('PATH', '').split(os.pathsep)
    for p in env_path:
        flang_new = os.path.join(p, 'flang-new')
        if os.path.isfile(flang_new):
            return True
    return False


def get_flang_new_lib_dir():
    try:
        output = subprocess.check_output(['flang-new', '--version'])
    except (OSError, subprocess.CalledProcessError):
        pass
    else:
        flang_dir = output.splitlines()[-1].split()[-1].strip().decode("utf-8")
        return os.path.normpath(os.path.join(flang_dir, '..', 'lib'))
    return None


def get_path_env_var(var):
    env_var = os.environ.get(var, None)
    if isinstance(env_var, str) and env_var.lower() == 'none':
        env_var = None
    if isinstance(env_var, str) and not os.path.exists(env_var):
        env_var = None
    return env_var


def have_lapack():
    lapack_env = get_path_env_var('LAPACK')
    return lapack_env is not None


def have_openblas():
    blas_env = get_path_env_var('BLAS')
    return blas_env and 'openblas' in blas_env


def append_env_var(env, var, value):
    env[var] = '{} {}'.format(env.get(var, ''), value)


def pip_package(name=None, try_import=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            _name = name if name else func.__name__
            try:
                module_name = get_module_name(_name)
                importlib.import_module(module_name)
                importlib.invalidate_caches()
            except (ImportError, ModuleNotFoundError):
                info("Installing required dependency: {} ... ", _name)
                func(*args, **kwargs)
                if try_import:
                    import site
                    site.main()
                    importlib.invalidate_caches()
                    importlib.import_module(module_name)
                info("{} installed successfully", _name)
        return wrapper
    return decorator


def run_cmd(args, msg="", failOnError=True, cwd=None, env=None, quiet=False, **kwargs):
    cwd_log = "cd " + cwd + " ;" if cwd else ""
    print("+", cwd_log, ' '.join(args))
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=quiet, **kwargs)
    if failOnError and result.returncode != 0:
        xit_msg = [msg]
        if result.stdout:
            xit_msg.append("stdout:")
            xit_msg.append(result.stdout.decode("utf-8"))
        if result.stderr:
            xit_msg.append("stderr:")
            xit_msg.append(result.stderr.decode("utf-8"))
        xit("{}", os.linesep.join(xit_msg))
    return result.returncode


def known_packages():
    @pip_package()
    def pytest(**kwargs):
        setuptools(**kwargs)
        wcwidth(**kwargs)
        pluggy(**kwargs)
        atomicwrites(**kwargs)
        more_itertools(**kwargs)
        attrs(**kwargs)
        packaging(**kwargs)
        py(**kwargs)
        install_from_pypi("pytest==5.1.0", **kwargs)

    @pip_package()
    def pytest_parallel(**kwargs):
        pytest(**kwargs)
        install_from_pypi("pytest-parallel==0.0.9", **kwargs)

    @pip_package()
    def py(**kwargs):
        install_from_pypi("py==1.8.0", **kwargs)

    @pip_package()
    def attrs(**kwargs):

        install_from_pypi("attrs==19.2.0", **kwargs)

    @pip_package()
    def pyparsing(**kwargs):
        install_from_pypi("pyparsing==2.4.2", **kwargs)

    @pip_package()
    def packaging(**kwargs):
        six(**kwargs)
        pyparsing(**kwargs)
        install_from_pypi("packaging==19.0", **kwargs)

    @pip_package()
    def more_itertools(**kwargs):
        install_from_pypi("more-itertools==7.0.0", **kwargs)

    @pip_package()
    def atomicwrites(**kwargs):
        install_from_pypi("atomicwrites==1.3.0", **kwargs)

    @pip_package()
    def pluggy(**kwargs):
        zipp(**kwargs)
        install_from_pypi("pluggy==0.13.1", **kwargs)

    @pip_package()
    def zipp(**kwargs):
        setuptools_scm(**kwargs)
        install_from_pypi("zipp==0.5.0", **kwargs)

    @pip_package()
    def wcwidth(**kwargs):
        six(**kwargs)
        install_from_pypi("wcwidth==0.1.7", **kwargs)

    @pip_package()
    def PyYAML(**kwargs):
        install_from_pypi("PyYAML==3.13", **kwargs)

    @pip_package()
    def six(**kwargs):
        install_from_pypi("six==1.16.0", **kwargs)

    @pip_package()
    def threadpoolctl(**kwargs):
        install_with_pip("threadpoolctl==2.2.0", **kwargs)

    @pip_package()
    def joblib(**kwargs):
        install_with_pip("joblib==1.2.0", **kwargs)

    @pip_package()
    def cppy(**kwargs):
        setuptools_scm(**kwargs)
        install_from_pypi("cppy==1.2.1", **kwargs)

    @pip_package()
    def kiwisolver(**kwargs):
        cppy(**kwargs)
        install_with_pip("kiwisolver==1.4.4", **kwargs)

    @pip_package()
    def python_dateutil(**kwargs):
        install_with_pip("python_dateutil==2.8.2", **kwargs)

    @pip_package()
    def Cython(extra_opts=None, **kwargs):
        if extra_opts is None:
            extra_opts = []
        install_from_pypi("Cython==0.29.32", extra_opts=['--no-cython-compile'] + extra_opts, **kwargs)

    @pip_package()
    def pybind11(**kwargs):
        install_from_pypi("pybind11==2.10.0", **kwargs)

    @pip_package()
    def pythran(**kwargs):
        install_from_pypi("pythran==0.12.0", **kwargs)

    @pip_package()
    def setuptools(**kwargs):
        six(**kwargs)
        install_from_pypi("setuptools==63.2.0", **kwargs)

    @pip_package()
    def pkgconfig(**kwargs):
        install_from_pypi("pkgconfig==1.5.1", **kwargs)

    @pip_package()
    def wheel(**kwargs):
        install_from_pypi("wheel==0.38.*", **kwargs)

    @pip_package()
    def protobuf(**kwargs):
        install_from_pypi("protobuf==3.8.0", **kwargs)

    @pip_package()
    def Keras_preprocessing(**kwargs):
        install_from_pypi("Keras-Preprocessing==1.0.5", **kwargs)

    @pip_package()
    def gast(**kwargs):
        install_from_pypi("gast==0.2.2", **kwargs)

    @pip_package()
    def astor(**kwargs):
        install_from_pypi("astor==0.8.0", **kwargs)

    @pip_package()
    def absl_py(**kwargs):
        install_from_pypi("absl-py==0.7.1", **kwargs)

    @pip_package()
    def mock(**kwargs):
        install_from_pypi("mock==3.0.5", **kwargs)

    @pip_package()
    def Markdown(**kwargs):
        install_from_pypi("Markdown==3.1.1", **kwargs)

    @pip_package()
    def Werkzeug(**kwargs):
        install_from_pypi("Werkzeug==0.15.4", **kwargs)

    @pip_package()
    def h5py(**kwargs):
        numpy(**kwargs)
        Cython(**kwargs)
        install_from_pypi("h5py==2.10.0", **kwargs)

    @pip_package()
    def sortedcontainers(**kwargs):
        install_from_pypi("sortedcontainers==2.1.0", **kwargs)

    @pip_package()
    def hypothesis(**kwargs):
        setuptools(**kwargs)
        attrs(**kwargs)
        sortedcontainers(**kwargs)
        install_from_pypi("hypothesis==5.41.1", **kwargs)

    @pip_package()
    def setuptools_scm(**kwargs):
        setuptools(**kwargs)
        install_with_pip("setuptools_scm==7.1.0", **kwargs)

    @pip_package()
    def numpy(**kwargs):
        install_with_pip("Cython", **kwargs)
        install_with_pip("numpy", **kwargs)

        # print numpy configuration
        if sys.implementation.name != 'graalpy' or __graalpython__.platform_id != 'managed':
            info("----------------------------[ numpy configuration ]----------------------------")
            run_cmd([sys.executable, "-c", 'import numpy as np; print(np.__version__); print(np.show_config())'])
            info("-------------------------------------------------------------------------------")

    @pip_package()
    def dateutil(**kwargs):
        setuptools_scm(**kwargs)
        install_from_pypi("python-dateutil==2.7.5", **kwargs)

    @pip_package()
    def certifi(**kwargs):
        install_from_pypi("certifi==2020.11.8", **kwargs)

    @pip_package()
    def idna(**kwargs):
        install_from_pypi("idna==2.8", **kwargs)

    @pip_package()
    def chardet(**kwargs):
        install_from_pypi("chardet==3.0.4", **kwargs)

    @pip_package()
    def urllib3(**kwargs):
        install_from_pypi("urllib3==1.25.6", **kwargs)

    @pip_package()
    def requests(**kwargs):
        idna(**kwargs)
        certifi(**kwargs)
        chardet(**kwargs)
        urllib3(**kwargs)
        install_from_pypi("requests==2.22", **kwargs)

    @pip_package()
    def lightfm(**kwargs):
        # pandas(**kwargs)
        requests(**kwargs)
        install_from_pypi("lightfm==1.15", **kwargs)

    @pip_package()
    def meson(**kwargs):
        install_from_pypi("meson==1.0.0", **kwargs)

    @pip_package()
    def ninja(**kwargs):
        install_with_pip("scikit-build==0.16.6")
        ninja_build_env = {}
        if sys.platform.startswith('linux'):
            ninja_build_env = {
                'CC': 'gcc',
                'CXX': 'g++',
            }
        install_from_pypi("ninja==1.11.1", env=ninja_build_env, **kwargs)

    @pip_package()
    def pytz(**kwargs):
        install_from_pypi("pytz==2022.2.1", **kwargs)

    @pip_package()
    def pandas(**kwargs):
        pytz(**kwargs)
        six(**kwargs)
        dateutil(**kwargs)
        numpy(**kwargs)

        install_from_pypi("pandas==1.5.2", **kwargs)

    @pip_package()
    def scipy(**kwargs):
        install_with_pip("scipy", **kwargs)

    @pip_package()
    def scikit_learn(**kwargs):
        # honor following selected env variables: BLAS, LAPACK, ATLAS
        scikit_learn_build_env = {}
        for key in ("BLAS", "LAPACK", "ATLAS"):
            if key in os.environ:
                scikit_learn_build_env[key] = os.environ[key]

        if sys.implementation.name == "graalpy":
            if not os.environ.get("VIRTUAL_ENV", None):
                xit("scikit-learn can only be installed within a venv.")
            from distutils.sysconfig import get_config_var
            scikit_learn_build_env["LDFLAGS"] = get_config_var("LDFLAGS")

        # install dependencies
        numpy(**kwargs)
        scipy(**kwargs)
        joblib(**kwargs)
        threadpoolctl(**kwargs)

        install_from_pypi("scikit-learn==1.1.3", env=scikit_learn_build_env, **kwargs)

    @pip_package()
    def cycler(**kwargs):
        six(**kwargs)
        install_from_pypi("cycler==0.11.0", **kwargs)

    @pip_package()
    def tox(**kwargs):
        install_from_pypi("tox==3.24.5", **kwargs)

    @pip_package()
    def cassowary(**kwargs):
        install_from_pypi("cassowary==0.5.2", **kwargs)

    @pip_package(name="PIL")
    def Pillow(**kwargs):
        setuptools(**kwargs)
        build_env = {"MAX_CONCURRENCY": "0"}
        build_cmd = ["build_ext", "--disable-jpeg"]
        zlib_root = os.environ.get("ZLIB_ROOT", None)
        if zlib_root:
            build_cmd += ["-I", os.path.join(zlib_root, "include"), "-L", os.path.join(zlib_root, "lib")]
        else:
            info("If Pillow installation fails due to missing zlib, try to set environment variable ZLIB_ROOT.")
        install_from_pypi("Pillow==9.2.0", build_cmd=build_cmd, env=build_env, **kwargs)

    @pip_package()
    def matplotlib(**kwargs):
        setuptools(**kwargs)
        certifi(**kwargs)
        cycler(**kwargs)
        cassowary(**kwargs)
        pyparsing(**kwargs)
        python_dateutil(**kwargs)
        numpy(**kwargs)
        Pillow(**kwargs)
        kiwisolver(**kwargs)

        def download_freetype(extracted_dir):
            target_dir = os.path.join(extracted_dir, "build")
            os.makedirs(target_dir, exist_ok=True)
            package_pattern = os.environ.get("GINSTALL_PACKAGE_PATTERN", "https://sourceforge.net/projects/freetype/files/freetype2/2.6.1/%s.tar.gz")
            _download_with_curl_and_extract(target_dir, package_pattern % "freetype-2.6.1")

        install_from_pypi("matplotlib==3.3.3", pre_install_hook=download_freetype, **kwargs)

    return locals()


KNOWN_PACKAGES = known_packages()
_KNOW_PACKAGES_FILES = dict()


def get_file_for_package(package, version):
    return _KNOW_PACKAGES_FILES.get((package, version), None)


def set_file_for_package(pth):
    package, version = package_from_path(pth)
    _KNOW_PACKAGES_FILES[(package, version)] = pth
    return package


def xit(fmt, *args, **kwargs):
    error(fmt, *args, **kwargs)
    exit(-1)


def _download_with_curl_and_extract(dest_dir, url, quiet=False):
    name = url[url.rfind("/")+1:]

    downloaded_path = os.path.join(dest_dir, name)

    # first try direct connection
    if run_cmd(["curl", "-L", "-o", downloaded_path, url], failOnError=False, quiet=quiet) != 0:
        # honor env var 'HTTP_PROXY', 'HTTPS_PROXY', and 'NO_PROXY'
        env = os.environ
        curl_opts = []
        using_proxy = False
        if url.startswith("http://") and "HTTP_PROXY" in env:
            curl_opts += ["--proxy", env["HTTP_PROXY"]]
            using_proxy = True
        elif url.startswith("https://") and "HTTPS_PROXY" in env:
            curl_opts += ["--proxy", env["HTTPS_PROXY"]]
            using_proxy = True
        if using_proxy and "NO_PROXY" in env:
            curl_opts += ["--noproxy", env["NO_PROXY"]]
        run_cmd(["curl", "-L"] + curl_opts + ["-o", downloaded_path, url], msg="Download error", quiet=quiet)

    if name.endswith(".tar.gz"):
        run_cmd(["tar", "xzf", downloaded_path, "-C", dest_dir], msg="Error extracting tar.gz", quiet=quiet)
        bare_name = name[:-len(".tar.gz")]
    elif name.endswith(".tar.bz2"):
        run_cmd(["tar", "xjf", downloaded_path, "-C", dest_dir], msg="Error extracting tar.bz2", quiet=quiet)
        bare_name = name[:-len(".tar.bz2")]
    elif name.endswith(".zip"):
        run_cmd(["unzip", "-u", downloaded_path, "-d", dest_dir], msg="Error extracting zip", quiet=quiet)
        bare_name = name[:-len(".zip")]
    else:
        xit("Unknown file type: {!s}", name)

    return bare_name


def _install_from_url(url, package, extra_opts=None, add_cflags="", ignore_errors=False, env=None, version=None,
                      pre_install_hook=None, build_cmd=None, debug_build=False, with_meson=False):
    if build_cmd is None:
        build_cmd = []
    if env is None:
        env = {}
    if extra_opts is None:
        extra_opts = []
    tempdir = tempfile.mkdtemp()

    quiet = "-q" in extra_opts

    os_env = os.environ

    # honor env var 'CFLAGS' and the explicitly passed env
    setup_env = os_env.copy()
    setup_env.update(env)
    cflags = os_env.get("CFLAGS", "") + ((" " + add_cflags) if add_cflags else "")
    setup_env['CFLAGS'] = cflags if cflags else ""

    user_build_cmd = os_env.get("GINSTALL_BUILD_CMD", "")
    if user_build_cmd:
        build_cmd = user_build_cmd.split(" ")

    bare_name = _download_with_curl_and_extract(tempdir, url, quiet=quiet)
    extracted_dir = os.path.join(tempdir, bare_name, "")

    file_realpath = os.path.dirname(os.path.realpath(__file__))
    patches_dir = os.path.join(Path(file_realpath).parent, 'patches', package)
    # empty match group to have the same groups range as in pip_hook
    # unlike with pip, the version number may not be available at all
    versions = re.search("()(\\d+)?(.\\d+)?(.\\d+)?", "" if version is None else version)

    if "--no-autopatch" not in extra_opts:
        # run autopatch_capi
        spec = importlib.util.spec_from_file_location("autopatch_capi", os.path.join(file_realpath, "autopatch_capi.py"))
        autopatch_capi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(autopatch_capi)
        info("auto-patching {}", extracted_dir)
        autopatch_capi.auto_patch_tree(extracted_dir)

    patch_file_path = first_existing(package, versions, get_sdist_patch(patches_dir), ".patch")
    if patch_file_path:
        run_cmd(["patch", "-d", extracted_dir, "-p1", "-i", patch_file_path], quiet=quiet)

    whl_patches_dir = os.path.join(patches_dir, "whl")
    patch_file_path = first_existing(package, versions, whl_patches_dir, ".patch")
    subdir = read_first_existing(package, versions, whl_patches_dir, ".dir")
    subdir = "" if subdir is None else subdir
    if patch_file_path:
        os.path.join(tempdir, bare_name, subdir)
        run_cmd(["patch", "-d", os.path.join(tempdir, bare_name, subdir), "-p1", "-i", patch_file_path], quiet=quiet)

    tmp_cwd = os.path.join(tempdir, bare_name)
    if pre_install_hook:
        pre_install_hook(tmp_cwd)

    if "--user" not in extra_opts and "--prefix" not in extra_opts and site.ENABLE_USER_SITE:
        user_arg = ["--user"]
    else:
        user_arg = []

    start = time.time()
    if with_meson:
        for cmd in [
            ['meson', 'setup', f'--prefix={os.environ.get("VIRTUAL_ENV")}', 'build'],
            ['meson', 'compile', '-C', 'build', '--ninja-args=-j4'],  # limit concurrency to 4
            ['meson', 'install', '-C', 'build'],
        ]:
            status = run_cmd(cmd, env=setup_env, cwd=tmp_cwd, quiet=quiet)
            if status != 0 and not ignore_errors:
                xit(f"An error occurred trying to run `{' '.join(cmd)}'")
    else:
        cmd = [sys.executable]
        if debug_build and sys.implementation.name == 'graalpy':
            cmd += ["-debug-java", "--python.ExposeInternalSources", "--python.WithJavaStacktrace=2"]
        cmd += ["setup.py"] + build_cmd + ["install"] + user_arg + extra_opts
        status = run_cmd(cmd, env=setup_env, cwd=tmp_cwd, quiet=quiet)
        if status != 0 and not ignore_errors:
            xit("An error occurred trying to run `setup.py install {!s} {}'", user_arg, " ".join(extra_opts))

    end = time.time()
    if quiet:
        info("{} successfully installed (took {:.2f} s)", package, (end - start))


# NOTE: Following 3 functions are duplicated in pip_hook.py:
# creates a search list of a versioned file:
# {name}-X.Y.Z.{suffix}, {name}-X.Y.{suffix}, {name}-X.{suffix}, {name}.{suffix}
# 'versions' is a result of re.search
def list_versioned(pkg_name, versions, dir, suffix):
    acc = ""
    res = []
    for i in range(2,5):
        v = versions.group(i)
        if v is not None:
            acc = acc + v
            res.append(acc)
    res.reverse()
    res = [os.path.join(dir, pkg_name + "-" + ver + suffix) for ver in res]
    res.append(os.path.join(dir, pkg_name + suffix))
    return res


def first_existing(pkg_name, versions, dir, suffix):
    for filename in list_versioned(pkg_name, versions, dir, suffix):
        if os.path.exists(filename):
            return filename


def read_first_existing(pkg_name, versions, dir, suffix):
    filename = first_existing(pkg_name, versions, dir, suffix)
    if filename:
        with open(filename, "r") as f:
            return f.read()

# end of code duplicated in pip_hook.py

def get_sdist_patch(patch_dir):
    sdist = os.path.join(patch_dir, "sdist")
    return sdist if os.path.isdir(sdist) else patch_dir


def install_with_pip(package, msg="", failOnError=False, **kwargs):
    for kw in ['extra_opts', 'debug_build']:
        if kw in kwargs:
            del kwargs[kw]
    run_cmd([sys.executable, "-m", "pip", "install", package], msg=msg, failOnError=failOnError, **kwargs)


def package_from_path(pth):
    assert os.path.exists(pth)
    package = os.path.splitext(os.path.split(pth)[-1])[0]
    version = None
    if "-" in package:
        package, _, version = package.rpartition("-")
    return package, version


def install_from_pypi(package, extra_opts=None, add_cflags="", ignore_errors=True, env=None, pre_install_hook=None,
                      build_cmd=None, debug_build=False, with_meson=False):
    if build_cmd is None:
        build_cmd = []
    if extra_opts is None:
        extra_opts = []
    package_pattern = os.environ.get("GINSTALL_PACKAGE_PATTERN", "https://pypi.org/pypi/%s/json")
    package_version_pattern = os.environ.get("GINSTALL_PACKAGE_VERSION_PATTERN", "https://pypi.org/pypi/%s/%s/json")

    version = None
    if "==" in package:
        package, _, version = package.rpartition("==")
        url = package_version_pattern % (package, version)
    else:
        url = package_pattern % package

    # check to see if we want to install the package from a file
    pth = get_file_for_package(package, version)
    if pth:
        url = f"file://{os.path.abspath(pth)}"
        warn(f"[install] installing '{package}' from '{url}'")

    if any(url.endswith(ending) for ending in [".zip", ".tar.bz2", ".tar.gz"]):
        # this is already the url to the actual package
        pass
    else:
        r = subprocess.check_output("curl -L %s" % url, stderr=subprocess.DEVNULL, shell=True).decode("utf8")
        url = None
        try:
            urls = json.loads(r)["urls"]
        except:
            pass
        else:
            for url_info in urls:
                if url_info["python_version"] == "source":
                    url = url_info["url"]
                    break

    # make copy of env
    env = env.copy() if env is not None else os.environ.copy()
    from distutils.sysconfig import get_config_var

    def set_if_exists(env_var, conf_var):
        conf_value = get_config_var(conf_var)
        if conf_value:
            env.setdefault(env_var, conf_value)

    set_if_exists("CC", "CC")
    set_if_exists("CXX", "CXX")
    set_if_exists("AR", "AR")
    set_if_exists("RANLIB", "RANLIB")
    set_if_exists("CFLAGS", "CFLAGS")
    set_if_exists("LDFLAGS", "CCSHARED")

    if url:
        _install_from_url(url, package=package, extra_opts=extra_opts, add_cflags=add_cflags,
                          ignore_errors=ignore_errors, env=env, version=version, pre_install_hook=pre_install_hook,
                          build_cmd=build_cmd, debug_build=debug_build, with_meson=with_meson)
    else:
        xit("Package not found: '{!s}'", package)


def get_site_packages_path():
    if site.ENABLE_USER_SITE:
        return site.getusersitepackages()
    else:
        for s in site.getsitepackages():
            if s.endswith("site-packages"):
                return s
    return None


def main(argv):
    parser = argparse.ArgumentParser(description="The simple Python package installer for GraalVM")
    parser.add_argument("--quiet", "-q", action="store_true", help="Do not show build output")

    subparsers = parser.add_subparsers(title="Commands", dest="command", metavar="Use COMMAND --help for further help.")

    subparsers.add_parser(
        "list",
        help="list locally installed packages"
    )

    install_parser = subparsers.add_parser(
        "install", help="install a known package",
        description="Install a known package. Known packages are:\n" + "\n".join(sorted(KNOWN_PACKAGES.keys())),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    install_parser.add_argument("package", help="comma-separated list")
    install_parser.add_argument("--prefix", help="user-site path prefix")
    install_parser.add_argument("--user", action='store_true', help="install into user site")
    install_parser.add_argument("--debug-build", action="store_true", help="Enable debug options when building")
    install_parser.add_argument("--no-autopatch", action="store_true", help="Do not autopatch C extensions.")

    uninstall_parser = subparsers.add_parser(
        "uninstall", help="remove installation folder of a local package", )
    uninstall_parser.add_argument("package", help="comma-separated list")

    pypi_parser = subparsers.add_parser(
        "pypi", help="attempt to install a package from PyPI (untested, likely won't work, and it won't install "
                     "dependencies for you)",
        description="Attempt to install a package from PyPI")
    pypi_parser.add_argument("package", help="comma-separated list, can use `==` at the end of a package name to "
                                             "specify an exact version")

    args = parser.parse_args(argv)

    quiet_flag = ["-q"] if args.quiet else []

    if args.command == "list":
        user_site = get_site_packages_path()
        info("Installed packages:")
        for p in sys.path:
            if p.startswith(user_site):
                info(p[len(user_site) + 1:])
    elif args.command == "uninstall":
        warn("WARNING: I will only delete the package folder, proper uninstallation is not supported at this time.")
        user_site = get_site_packages_path()
        for pkg in args.package.split(","):
            deleted = False
            p = None
            for p in sys.path:
                if p.startswith(user_site):
                    # +1 due to the path separator
                    pkg_name = p[len(user_site)+1:]
                    if pkg_name.startswith(pkg):
                        if os.path.isdir(p):
                            shutil.rmtree(p)
                        else:
                            os.unlink(p)
                        deleted = True
                        break
            if deleted:
                info("Deleted {}", p)
            else:
                xit("Unknown package: '{!s}'", pkg)
    elif args.command == "install":
        extra_opts = [] + quiet_flag
        if args.prefix:
            extra_opts += ["--prefix", args.prefix]
        if args.user:
            extra_opts += ["--user"]
        if args.no_autopatch:
            extra_opts += ["--no-autopatch"]

        for pkg in args.package.split(","):
            if os.path.isfile(pkg):
                warn("installing from file: {}".format(pkg))
                pkg = set_file_for_package(pkg)

            if pkg not in KNOWN_PACKAGES:
                warn("package: '%s' not found in known packages, installing with pip" % pkg)
                install_with_pip(pkg, msg="Unknown package: '{!s}'".format(pkg), failOnError=True)
            else:
                KNOWN_PACKAGES[pkg](extra_opts=extra_opts, debug_build=args.debug_build)
    elif args.command == "pypi":
        for pkg in args.package.split(","):
            install_from_pypi(pkg, extra_opts=quiet_flag, ignore_errors=False)


if __name__ == "__main__":
    main(sys.argv[1:])
