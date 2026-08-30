{
  lib,
  python3Packages,
  gobject-introspection,
  wrapGAppsHook3,
  gtk3,
  gdk-pixbuf,
  at-spi2-core,
  libwnck,
  gtk-layer-shell,
  grim,
  # Screenshot helpers are only needed for the OpenCV backend on Wayland.
  withWaylandScreenshot ? true,
}:

python3Packages.buildPythonApplication rec {
  pname = "hints";
  version = "0.1.1";
  format = "setuptools";

  src = lib.cleanSource ../.;

  # setup.py runs a PostInstallCommand that shells out to `uv` and writes a
  # systemd unit into $HOME. Neither works (nor is wanted) in a Nix build: the
  # unit is provided by the NixOS module instead.
  postPatch = ''
    substituteInPlace setup.py \
      --replace-fail '    cmdclass={"install": PostInstallCommand},' "" \
      --replace-fail '"PyGObject==3.50.0"' '"PyGObject"'
  '';

  nativeBuildInputs = [
    gobject-introspection
    wrapGAppsHook3
    python3Packages.setuptools
  ];

  buildInputs = [
    gtk3
    gdk-pixbuf
    at-spi2-core
    libwnck
    gtk-layer-shell
  ];

  dependencies = with python3Packages; [
    pygobject3
    pycairo
    pillow
    pyscreenshot
    opencv4
    numpy
    evdev
    dbus-python
    rich
  ];

  # buildPythonApplication's own wrapper would fight wrapGAppsHook3 over the
  # GI_TYPELIB_PATH, so let the gapps hook do the final wrapping.
  dontWrapGApps = true;

  makeWrapperArgs = [
    "\${gappsWrapperArgs[@]}"
  ]
  ++ lib.optionals withWaylandScreenshot [
    "--suffix"
    "PATH"
    ":"
    (lib.makeBinPath [
      grim
    ])
  ];

  # Expose the GNOME Shell extension where gnome-shell looks for it, so that
  # putting this package in environment.systemPackages is enough.
  postInstall = ''
    mkdir -p $out/share/gnome-shell/extensions
    ln -s $out/${python3Packages.python.sitePackages}/hints/extensions/gnome/hints@realh.co.uk \
      $out/share/gnome-shell/extensions/hints@realh.co.uk
  '';

  # There is no test suite; just make sure the entry points import cleanly.
  doCheck = false;

  pythonImportsCheck = [
    "hints"
    "hints.cli"
  ];

  meta = {
    description = "Navigate GUI applications in Linux without a mouse by typing hints";
    homepage = "https://github.com/DemyCode/hints";
    license = lib.licenses.gpl3Only;
    mainProgram = "hints";
    platforms = lib.platforms.linux;
  };
}
