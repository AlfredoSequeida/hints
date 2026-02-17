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

> [!IMPORTANT]
>
> - You need to have some sort of [compositing](https://wiki.archlinux.org/title/Xorg#Composite) setup so that you can properly see hints on top of windows with the correct level of transparency. If you run hints and see an opaque/black window rather than a transparent window; this is probably why.

> [!NOTE]  
> The install script below does the following:
>
> 1. Installs any required system dependencies for Ubuntu, Arch, and Fedora systems. If you don't run any of those distros, you can look at the install script to see what you need to install.
> 2. Temporarily installs [UV](https://docs.astral.sh/uv/).
> 3. Uses [uv tool](https://docs.astral.sh/uv/guides/tools) to install the latest version of hints.
> 4. Cleans up leftover files.

Run the install script:

```
curl -fsSL https://raw.githubusercontent.com/AlfredoSequeida/hints/main/install.sh | bash
```

## Setup

1. To facilitate setup, hints ships with a setup script.

To setup hints run:

```
sudo env XDG_SESSION_TYPE=$XDG_SESSION_TYPE env XDG_CURRENT_DESKTOP=$XDG_CURRENT_DESKTOP $(whereis hints | awk '{print $2}') --setup
```

2. At this point you're pretty much done. You can verify this by running `hints` in a terminal emulator. However, you should bind hints to your keyboard so that you can summon hints on command. This is very desktop environment / window manager specific, but to get you started here are some examples for popular systems:

- [i3/sway](https://github.com/AlfredoSequeida/hints/wiki/Window-Manager-and-Desktop-Environment-Setup-Guide#setup-keyboard-shortcuts-1)
- [Hyprland](https://github.com/AlfredoSequeida/hints/wiki/Window-Manager-and-Desktop-Environment-Setup-Guide#setup-keyboard-shortcuts-3)
- [Gnome](https://github.com/AlfredoSequeida/hints/wiki/Window-Manager-and-Desktop-Environment-Setup-Guide#setup-keyboard-shortcuts-4)

> [!NOTE]  
> If you still don't see any hints, the application you're testing could need a bit of extra setup. Please see the [Help,-hints-doesn't-work-with-X-application](https://github.com/AlfredoSequeida/hints/wiki/Help,-hints-doesn't-work-with-X-application) page in the wiki.

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

3. Install hints as an editable package (from the repository's root directory):

```
pip install -e .
```

At this point, hints should be installed locally in the virtual environment, you can run `hints` in your shell to launch it. Any edits you make to the source code will automatically update the installation. For future development work, you can simply re-enable the virtual environment (step 2).

## Development tips

- If you are making updates that impact hints, you will most likely need to test displaying hints and might find yourself executing hints but not being quick enough to switch to a window to see hints. To get around this, you can execute `hints` with a short pause in your shell: `sleep 0.5; hints`. This way you can have time to switch to a window and see any errors / logs in your shell.
- If `hints` is consuming all keyboard inputs and you're trapped: switch to a virtual terminal with e.g. <kbd>CTRL</kbd>+<kbd>ALT</kbd>+<kbd>F2</kbd>, login, and run `killall hints`. You can then exit with `exit` and switch back to the the previous session (most likely 1): <kbd>CTRL</kbd>+<kbd>ALT</kbd>+<kbd>F1</kbd>
