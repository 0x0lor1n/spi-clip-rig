{
  description = "ESP-Prog and a SOIC-8 test clip as an SPI flash reader, on an external 3.3 V supply";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    mcu-bench = {
      url = "github:0x0lor1n/mcu-bench";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      mcu-bench,
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAll = f: nixpkgs.lib.genAttrs systems (s: f nixpkgs.legacyPackages.${s});
      bench = pkgs: mcu-bench.lib pkgs;
      python = pkgs: (bench pkgs).python (_: [ ]);
    in
    {
      packages = forAll (
        pkgs:
        let
          b = bench pkgs;
        in
        rec {
          # docs/{schematic,wiring}.{svg,png} are tracked; `render-docs` copies this output over them.
          # SVG for GitHub, PNG for chats (Telegram drops schemdraw's <use> text).
          docs =
            pkgs.runCommand "spi-clip-rig-docs" { nativeBuildInputs = [ (python pkgs) ] ++ b.renderInputs; }
              ''
                mkdir -p $out
                ${b.renderSchematic "${./src/schematic}/schematic.py" "$out/schematic"}
                ${b.renderD2 "${./docs}/wiring.d2" "$out/wiring"}
              '';

          render-docs = b.mkRenderDocs { };
          fizzel = b.mkFizzel "fizzel" "docs/bench.fzz";

          # docs/bench.fzz is tracked; `nix build .#bench-fzz` regenerates it from gen.py.
          bench-fzz = b.mkBenchFzz {
            name = "spi-clip-rig-bench-fzz";
            gen = ./src/fritzing/gen.py;
            python = python pkgs;
          };

          default = docs;
        }
      );

      devShells = forAll (pkgs: {
        default = (bench pkgs).mkDevShell {
          name = "spi-clip-rig";
          packages = with self.packages.${pkgs.stdenv.hostPlatform.system}; [
            render-docs
            fizzel
            pkgs.d2
            (python pkgs)
          ];
          commands = [
            [
              "render-docs"
              "regenerate docs/{schematic,wiring}.{svg,png} from src/schematic and wiring.d2"
            ]
            [
              "fizzel"
              "docs/bench.fzz in Fritzing"
            ]
            [
              "nix build .#bench-fzz"
              "regenerate bench.fzz from src/fritzing/gen.py"
            ]
            [
              "nix flake check"
              "Fritzing lint, docs/bench freshness"
            ]
            [
              "lefthook run pre-commit"
              "what the commit hook runs (gitleaks, nixfmt, deadnix, statix, ruff)"
            ]
            [
              "lefthook run pre-push"
              "what the push hook runs (nix flake check)"
            ]
          ];
        };
      });

      checks = forAll (
        pkgs:
        let
          b = bench pkgs;
          pkg = self.packages.${pkgs.stdenv.hostPlatform.system};
        in
        {
          # PNG is not compared, resvg output is not byte-stable across versions.
          docs-fresh = b.mkFreshCheck "docs-fresh" pkg.docs ./docs [
            "schematic.svg"
            "wiring.svg"
          ];
          bench-fresh = b.mkFreshCheck "bench-fresh" pkg.bench-fzz ./docs [ "bench.fzz" ];
          bench-lint = b.mkBenchLint {
            fzz = pkg.bench-fzz;
            sketches = [ "bench" ];
            cases = ./src/fritzing/lint_cases.py;
            python = python pkgs;
          };
        }
      );
    };
}
