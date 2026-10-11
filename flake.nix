{
  description = "Native bitmap subtitle conversion CLI (Blu-ray PGS, DVD VobSub, HD-DVD SUP)";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = fn: nixpkgs.lib.genAttrs systems (system: fn (import nixpkgs { inherit system; }));
    in {
      packages = forAllSystems (pkgs: {
        default = pkgs.stdenv.mkDerivation {
          pname = "bdsup2sub-native";
          version = "0.1.0-test";
          src = self;
          nativeBuildInputs = with pkgs; [ cmake ninja pkg-config python3 ];
          buildInputs = with pkgs; [ libpng zlib ];
          cmakeFlags = [ "-DBDSUP2SUB_NATIVE_BUILD_TESTS=ON" ];
          doCheck = true;
          checkPhase = ''ctest --output-on-failure'';
          meta = with pkgs.lib; {
            description = "Native Blu-ray, DVD and HD-DVD bitmap subtitle converter";
            license = licenses.asl20;
            platforms = platforms.unix;
            mainProgram = "bdsup2sub";
          };
        };
      });
      apps = forAllSystems (pkgs: {
        default = { type = "app"; program = "${self.packages.${pkgs.system}.default}/bin/bdsup2sub"; };
      });
    };
}
