# Firmware builds that produce the offline harness's data dictionaries.
# Called by regen.sh with cb1-autopipette's pinned nixpkgs, so klipper.dict
# comes from the same Klipper source as the klippy the tests run.
{ nixpkgs }:
let
  pkgs = import nixpkgs { };
  fw =
    mcu: cfg:
    (pkgs.klipper-firmware.override {
      inherit mcu;
      firmwareConfig = cfg;
    }).overrideAttrs
      (old: {
        # Without a git checkout the dictionary's version starts with "?";
        # name the Klipper version instead (a build timestamp still follows).
        postPatch = (old.postPatch or "") + ''
          echo "${pkgs.klipper.version}-NixOS" > klippy/.version
        '';
        installPhase = old.installPhase + ''
          cp out/klipper.dict $out/klipper.dict
        '';
      });
in
{
  m8p = fw "manta-m8p-v2" ./m8p.config;
  octopus = fw "octopus-v1.1-f446" ./octopus.config;
  host = fw "host" ./host.config;
  klipperRev = pkgs.klipper.src.rev;
}
