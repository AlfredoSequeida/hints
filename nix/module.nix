{ self }:
{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.hints;
in
{
  options.services.hints = {
    enable = lib.mkEnableOption "hints, keyboard-driven GUI navigation";

    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.hints;
      defaultText = lib.literalMD "the `hints` package from this flake";
      description = "The hints package to use.";
    };

    users = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      example = [ "alice" ];
      description = ''
        Users to add to the `input` group. hints needs write access to
        `/dev/uinput` to synthesise mouse events.
      '';
    };

    daemon = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = ''
          Run `hintsd` as a systemd user service. The daemon keeps GTK/AT-SPI
          warm so that triggering hints is fast.
        '';
      };

      wantedBy = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ "graphical-session.target" ];
        example = [ "default.target" ];
        description = ''
          Targets that pull in the `hintsd` user service. The default only
          works if your session sets up `graphical-session.target` (GNOME, KDE,
          sway/Hyprland via uwsm or their systemd integration). Use
          `default.target` for sessions that do not.
        '';
      };
    };

    accessibility = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = ''
        Set the AT-SPI accessibility environment variables that the AT-SPI
        backend needs in order to enumerate GUI elements.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ];

    # /dev/uinput, used to synthesise clicks, scrolls and pointer moves.
    boot.kernelModules = [ "uinput" ];
    hardware.uinput.enable = true;

    services.udev.extraRules = ''
      KERNEL=="uinput", GROUP="input", MODE:="0660", OPTIONS+="static_node=uinput"
    '';

    users.users = lib.genAttrs cfg.users (_: {
      extraGroups = [ "input" ];
    });

    environment.sessionVariables = lib.mkIf cfg.accessibility {
      ACCESSIBILITY_ENABLED = "1";
      GNOME_ACCESSIBILITY = "1";
      GTK_MODULES = "gail:atk-bridge";
      OOO_FORCE_DESKTOP = "gnome";
      QT_ACCESSIBILITY = "1";
      QT_LINUX_ACCESSIBILITY_ALWAYS_ON = "1";
    };

    # The AT-SPI bus that the accessibility backend talks to.
    services.gnome.at-spi2-core.enable = true;

    systemd.user.services.hintsd = lib.mkIf cfg.daemon.enable {
      description = "Hints daemon";
      documentation = [ "https://github.com/DemyCode/hints" ];
      wantedBy = cfg.daemon.wantedBy;
      partOf = lib.optional (builtins.elem "graphical-session.target" cfg.daemon.wantedBy) "graphical-session.target";
      after = [ "graphical-session.target" ];
      serviceConfig = {
        Type = "simple";
        ExecStart = lib.getExe' cfg.package "hintsd";
        Restart = "always";
        RestartSec = "1s";
      };
    };
  };
}
