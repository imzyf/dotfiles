<h4 align="right"><a href="./README.md">中文</a> | <strong>English</strong></h4>

# dotfiles

My personal dotfiles, managed with [chezmoi](https://www.chezmoi.io/): one command bootstraps a fresh Mac.

## Bootstrap a new machine

On a new Apple Silicon Mac, open Terminal.app and run:

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply imzyf
```

Insert the YubiKey first: it holds the GPG private key `19084855608DB9D5`, and without it encrypted files cannot be decrypted. The first run prompts for the private GitLab name, email and host.

## Credits

Huge thanks to [liby/dotfiles](https://github.com/liby/dotfiles) — a lot of this code comes straight from there, and it solved so many headaches for me.
