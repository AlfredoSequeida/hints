<p align="center">
  <img src="https://github.com/user-attachments/assets/bca7fb8e-a4ad-435b-aa40-c26dbb017239" alt="hints" />

  <a href="https://youtu.be/b-NrnemxpBk" target="_blank">
    <img src="https://github.com/user-attachments/assets/e5b90967-8f95-4907-b6b6-2babad9b74f7" alt="I made Vimium for the Linux desktop | Use Linux without a mouse"/>
  </a>

  <a href="https://www.keytilt.xyz" target="_blank">
    <img src="https://github.com/user-attachments/assets/b44f8021-7f1f-4a60-9be4-561662266e96" alt="keytilt"/>
  </a>
</p>



# Click, scroll, and drag with your keyboard

![demo](https://github.com/user-attachments/assets/838d4043-5e21-4e61-979f-bd8fae7d4d36)

Navigate GUIs without a mouse by typing hints in combination with modifier keys.

- click once (<kbd>j</kbd><kbd>k</kbd>)
- click multiple times (<kbd>2</kbd><kbd>j</kbd><kbd>k</kbd>)
- right click (<kbd>SHIFT</kbd> + <kbd>j</kbd><kbd>k</kbd>)
- drag (<kbd>ALT</kbd> + <kbd>j</kbd><kbd>k</kbd>)
   - Note for wayland users: Due to how different wayland compositors handle overlay windows, dragging might not always work for your compositor.
- hover (<kbd>CTRL</kbd> + <kbd>j</kbd><kbd>k</kbd>)
- scroll/move the mouse using vim key bindings (<kbd>h</kbd>,<kbd>j</kbd>,<kbd>k</kbd>,<kbd>l</kbd>)

Don't like the keybindings? That's ok, you can change them.

# Installing

> [!NOTE]
> Hints WILL NOT work on Gnome under Wayland. See [this](https://github.com/AlfredoSequeida/hints/issues/55) issue for an explanation. It WILL however work under X11.

## System Requirements

1. You will need to have some sort of [compositing](https://wiki.archlinux.org/title/Xorg#Composite) setup so that you can properly overlay hints over windows with the correct level of transparency. Otherwise, the overlay will just cover the entire screen; not allowing you to see what is under the overlay.

2. You will need to enable accessibility for your system. If you use a Desktop Environment, this might already be enabled by default. If you find that hints does not work or works for some apps and not others add the following to `/etc/environment`

```
ACCESSIBILITY_ENABLED=1
GTK_MODULES=gail:atk-bridge
OOO_FORCE_DESKTOP=gnome
GNOME_ACCESSIBILITY=1
QT_ACCESSIBILITY=1
QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
```

3. Hints comes with a daemon used to perform mouse actions. Without starting the daemon, you won't be able to perform mouse actions. If you are using the latest version of pipx (which will be installed below), everything should just work and you can skip this step. If you are not using the latest version of pipx or choose not to use pipx, you will need to set the `HINTS_EXPECTED_BIN_DIR` environment variable prior to installing hints. This path tells the `setup.py` script where hintsd is installed to properly create the service file. For example to use `$HOME/.local/bin` (the default for pipx), you can do `export HINTS_EXPECTED_BIN_DIR="$HOME/.local/bin"`.

4. Below you will find installation instructions for some popular linux distros. The commands below assume that you're running wayland if your `XDG_SESSION_TYPE` variable is set to `wayland`. If that's the case you will install the wayland dependencies. Otherwise, the x11 dependencies will be installed. The setup is as follows:

- Install the python/system dependencies (including [pipx](https://pipx.pypa.io/stable/installation/)).
- Setup pipx.
- Use pipx to install hints.

Ubuntu

```
sudo apt update && \
    sudo apt install git libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-4.0 pipx cmake libdbus-1-dev && \
    [ $XDG_SESSION_TYPE = "wayland" ] && sudo apt install gtk-layer-shell grim && \
    pipx ensurepath && \
    pipx install git+https://github.com/AlfredoSequeida/hints.git
```

Fedora

```
sudo dnf install git gcc gobject-introspection-devel cairo-gobject-devel pkg-config python3-devel gtk4 pipx && \
    [ $XDG_SESSION_TYPE = "wayland" ] && sudo dnf install gtk-layer-shell grim && \
    pipx ensurepath && \
    pipx install git+https://github.com/AlfredoSequeida/hints.git
```

Arch

```
sudo pacman -Sy && \
    sudo pacman -S git python cairo pkgconf gobject-introspection gtk4 python-pipx && \
    [ $XDG_SESSION_TYPE = "wayland" ] && sudo pacman -S gtk-layer-shell grim || sudo pacman -S libwnck3 && \
    pipx ensurepath && \
    pipx install git+https://github.com/AlfredoSequeida/hints.git
```

Finally, source your shell config or restart your terminal.

## Setup

1. Follow the setup instructions for your window system [here](https://github.com/AlfredoSequeida/hints/wiki/Window-Manager-and-Desktop-Environment-Setup-Guide).
2. Confirm that the uinput kernel module is loaded. If it is not 
`sudo modprobe uinput && echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf`
3. At this point, hints should be installed, you can verify this by running `hints` in your shell. If you still don't see any hints, the application you're testing could need a bit of extra setup. Please see the [Help,-hints-doesn't-work-with-X-application](https://github.com/AlfredoSequeida/hints/wiki/Help,-hints-doesn't-work-with-X-application) page in the wiki.

# Documentation

For a guide on configuring and using hints, please see the [Wiki](https://github.com/AlfredoSequeida/hints/wiki).

# Contributing

The easiest ways to contribute are to:

- [Become a sponsor](https://github.com/sponsors/AlfredoSequeida). Hints is a passion project that I really wanted for myself and I am working on it in my spare time. I chose to make it free and open source so that others can benefit. If you find it valuable, donating is a nice way to say thanks. You can donate any amount you want.
- Report bugs. If you notice something is not working as expected or have an idea on how to make hints better, [open up an issue](https://github.com/AlfredoSequeida/hints/issues/new). This helps everyone out.
- If you can code, feel free to commit some code! You can see if any issues need solutions or you can create a new feature. If you do want to create a new feature, it's a good idea to create an issue first so we can align on why this feature is needed and if it has a possibility of being merged.

## Development

If you want to help develop hints, first setup your environment:

1. Create a virtual environment for the project.

```
python3 -m venv venv
```

2. Activate your virtual environment for development. This will differ based on OS/shell. See the table [here](https://docs.python.org/3/library/venv.html#how-venvs-work) for instructions.

3. Install hints as an editable package (from the repositorie's root directory):

```
pip install -e .
```

At this point, hints should be installed locally in the virtual environment, you can run `hints` in your shell to launch it. Any edits you make to the source code will automatically update the installation. For future development work, you can simply re-enable the virtual environment (step 2).

## Development tips

- If you are making updates that impact hints, you will most likely need to test displaying hints and might find yourself executing hints but not being quick enough to switch to a window to see hints. To get around this, you can execute `hints` with a short pause in your shell: `sleep 0.5; hints`. This way you can have time to switch to a window and see any errors / logs in your shell.
- If `hints` is consuming all keyboard inputs and you're trapped: switch to a virtual terminal with e.g. <kbd>CTRL</kbd>+<kbd>ALT</kbd>+<kbd>F2</kbd>, login, and run `killall hints`. You can then exit with `exit` and switch back to the the previous session (most likely 1): <kbd>CTRL</kbd>+<kbd>ALT</kbd>+<kbd>F1</kbd>
