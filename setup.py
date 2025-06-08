import codecs
from os import getenv, path
from pathlib import Path
from re import M, search
from subprocess import run

from setuptools import setup
from setuptools.command.install import install


class CouldNotFindExpectedInstallDirectory(Exception):
    def __str__(self):
        return (
            "Could not find expected install directory. This is required to"
            " setup the hintsd service. Set the 'HINTS_EXPECTED_BIN_DIR'"
            " environment variable with the location hints will be installed"
            " in. For example:"
            " 'export HINTS_EXPECTED_BIN_DIR=\"$HOME/.local/bin\"'."
            " Then attemp to re-install."
        )


with open("README.md", "r") as fh:
    long_description = fh.read()

here = path.abspath(path.dirname(__file__))


def read(*parts):
    with codecs.open(path.join(here, *parts), "r") as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def get_bin_dir(self):
        bin_dir = ""

        try:
            pipx_bin_dir_cmd = run(
                ["pipx", "environment", "--value", "PIPX_BIN_DIR"],
                check=True,
                capture_output=True,
            )
            bin_dir = pipx_bin_dir_cmd.stdout.decode("utf-8").strip()
        except:  # pylint: disable=bare-except
            bin_dir = getenv("HINTS_EXPECTED_BIN_DIR", "")

        if not bin_dir:
            raise CouldNotFindExpectedInstallDirectory()

        return bin_dir

    def install_hintsd_service(self):
        """Install hintsd service for the current user."""
        bin_dir = self.get_bin_dir()
        if bin_dir:
            user_service_directory = Path(path.expanduser("~")) / ".config/systemd/user"
            user_service_directory.mkdir(parents=True, exist_ok=True)
            with open(
                user_service_directory / "hintsd.service",
                mode="w+",
                encoding="utf-8",
            ) as service_file:
                service_file.write(
                    "[Unit]\n"
                    "Description=Hints daemon\n"
                    "[Service]\n"
                    "Type=simple\n"
                    f"ExecStart={bin_dir}/hintsd\n"
                    "Restart=always\n"
                    "[Install]\n"
                    "WantedBy=default.target\n"
                )

    def run(self):
        install.run(self)
        self.install_hintsd_service()


dynamic_version = find_version("hints", "__init__.py")

s = setup(
    name="hints",
    version=dynamic_version,
    author="Alfredo Sequeida",
    description="Hints lets you navigate GUI applications in Linux without your"
    ' mouse by displaying "hints" you can type on your keyboard to interact'
    " with GUI elements.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AlfredoSequeida/hints",
    download_url="https://github.com/AlfredoSequeida/hints/archive/"
    + dynamic_version
    + ".tar.gz",
    keywords=[
        "vim",
        "vimium",
        "hints",
        "mouseless",
        "keyboard",
        "keyboard navigation",
        "linux",
        "x11",
        "wayland",
    ],
    python_requires=">=3.10",
    platforms=["Linux"],
    classifiers=[
        "Intended Audience :: End Users/Desktop",
        "Topic :: Desktop Environment",
        "Topic :: Desktop Environment :: Window Managers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
    ],
    license="GPLv3",
    packages=["hints", "hints.backends", "hints.huds", "hints.window_systems"],
    include_package_data=True,
    install_requires=[
        "PyGObject==3.50.0",
        "pillow",
        "pyscreenshot",
        "opencv-python",
        "evdev",
        "dbus-python",
    ],
    entry_points={
        "console_scripts": [
            "hints = hints.hints:main",
            "hintsd = hints.mouse_service:main",
        ]
    },
    cmdclass={"install": PostInstallCommand},
)
