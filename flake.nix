{
  description = "Hints - navigate GUI applications in Linux without your mouse";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      overlays.default = final: _prev: {
        hints = final.callPackage ./nix/package.nix { };
      };

      packages = forAllSystems (pkgs: rec {
        hints = pkgs.callPackage ./nix/package.nix { };
        default = hints;
      });

      nixosModules.default = import ./nix/module.nix { inherit self; };
      nixosModules.hints = self.nixosModules.default;

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          inputsFrom = [ self.packages.${pkgs.stdenv.hostPlatform.system}.hints ];
          packages = [
            pkgs.python3Packages.black
            pkgs.python3Packages.isort
            pkgs.python3Packages.pylint
          ];
        };
      });

      formatter = forAllSystems (pkgs: pkgs.nixfmt-tree);
    };
}
