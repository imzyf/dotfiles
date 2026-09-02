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

Huge thanks to [liby/dotfiles](https://github.com/liby/dotfiles), which solved so many headaches for me. Most files here use its version as is, kept in sync by [`sync-upstream.sh`](scripts/sync-upstream.sh).

A few files I have adapted to my own habits, so upstream can no longer overwrite them wholesale. For those, the upstream version is kept separately under `.chezmoitemplates/`, and the local file pulls that copy in with `includeTemplate` and layers my changes on top, leaving only the difference to maintain. That way I stand on the shoulders of giants, keep things the way I like them, and still pick up whatever upstream improves later.
