{
  description = "Daily Arxiv Paper Feed Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            (python3.withPackages (ps: with ps; [
              scrapy
              requests
              python-dotenv
              markdown
              tqdm
              pip
              virtualenv
            ]))
            bash
            git
          ];

          shellHook = ''
            # Create a venv if it doesn't exist for non-nixpkgs deps
            if [ ! -d ".venv" ]; then
              python -m venv .venv
              source .venv/bin/activate
              pip install langchain-google-genai langchain arxiv
            else
              source .venv/bin/activate
            fi
            export PYTHONPATH=$PWD:$PYTHONPATH
          '';
        };
      }
    );
}
