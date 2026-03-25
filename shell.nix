let
  nixpkgs = builtins.fetchTarball {
    name = "nixos-25.11-20260325";
    url = "https://github.com/NixOS/nixpkgs/archive/4590696c8693.tar.gz";
    sha256 = "1i2dygdxf20mkma168mgy85a1xzlhs16dmm1lcvxz3039mfwqxz1";
  };

  jdk = pkgs.openjdk25;

  pkgs = import nixpkgs { };
in
  pkgs.mkShell {
    buildInputs = [
      jdk
      pkgs.maven
      pkgs.pre-commit
    ];

    shellHook = ''
    '';
  }
