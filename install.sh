#!/bin/bash

UV_INSTALLATION_PATH=`mktemp -d`
BIN_DIR=""

print_instruction_header() {
  echo ""
  echo "####################################"
  echo "$1"
  echo "####################################"
  echo ""
}

install_dependencies_using_apt() {
  sudo apt update && \
  sudo apt install -y git libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-4.0 cmake libdbus-1-dev && \
  [ $XDG_SESSION_TYPE = "wayland" ] && sudo apt install -y libgtk-layer-shell0 grim
}

install_dependencies_using_pacman() {
  sudo pacman -Sy && \
  sudo pacman -S --noconfirm --needed git python cairo pkgconf gobject-introspection gtk4 && \
  [ $XDG_SESSION_TYPE = "wayland" ] && sudo pacman -S --noconfirm --needed gtk-layer-shell grim || sudo pacman -S --noconfirm --needed libwnck3
}

install_dependencies_using_dnf() {
  sudo dnf install -y git gcc cmake gobject-introspection-devel cairo-gobject-devel pkg-config python3-devel dbus-devel gtk4 && \
  [ $XDG_SESSION_TYPE = "wayland" ] && sudo dnf install -y gtk-layer-shell grim
}

available() { command -v "${1:?}" >/dev/null; }

install_system_dependencies() {
  print_instruction_header "Installing system dependencies."

  if available apt;
  then
    install_dependencies_using_apt
  elif available pacman;
  then
    install_dependencies_using_pacman
  elif available dnf;
  then
    install_dependencies_using_dnf
  else 
    echo "Could not find supported package manager, you will need to install hints manually. If you want your distribution to be supported by the install script, open an issue: https://github.com/AlfredoSequeida/hints/issues"
    exit 1
  fi
}

install_uv() {
  print_instruction_header "Installing UV."

  curl -LsSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 UV_INSTALL_DIR=$UV_INSTALLATION_PATH sh
  sudo chown -R $USER `$UV_INSTALLATION_PATH/uv tool dir`
  BIN_DIR=`$UV_INSTALLATION_PATH/uv tool dir --bin`
}

install_hints() {
  print_instruction_header "Installing hints."

  HINTS_EXPECTED_BIN_DIR="$BIN_DIR" $UV_INSTALLATION_PATH/uv tool install --force git+https://github.com/AlfredoSequeida/hints@feature/setup
  $UV_INSTALLATION_PATH/uv tool update-shell 
}

cleanup () {
  rm -r $UV_INSTALLATION_PATH
}

greet() {
  echo "" 
  echo "🌟 All done, to setup hints run the setup script:"
  echo "sudo env XDG_SESSION_TYPE=$XDG_SESSION_TYPE env XDG_CURRENT_DESKTOP=$XDG_CURRENT_DESKTOP $BIN_DIR/hints --setup"
  echo "" 
}

install_system_dependencies
install_uv
install_hints
cleanup
greet
