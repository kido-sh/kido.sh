# kido.sh

The website of [kido](https://github.com/kido-sh/kido), served by GitHub Pages at <https://kido.sh>.

- `index.html`: the landing page, one file with no external scripts or fonts.
- `docs/`: statically generated documentation pages. Hardware records live in `data/gpu/boards/*.json` and are built into `docs/` with `python3 scripts/build-docs.py`.
- `install.sh`: a copy of kido's `install.sh`, so `curl -fsSL https://kido.sh/install.sh | sh` works.
  Update it together with each kido release.
- `CNAME`: the custom domain.

Licensed under the Apache License 2.0, like kido.
