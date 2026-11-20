# Langfuse, run locally

[Langfuse](https://langfuse.com) records what an agent session did: every prompt, model
call, tool call and its result, with tokens, cost and duration. `make langfuse-install`
runs it on your own machine, and a Claude Code plugin sends your sessions to it.

It is optional and not part of `make install` or `make update`.

## What it keeps

**Everything a session read or wrote, in full, on your machine only.** That includes the
content of any file an agent opened, so a secret an agent read from a file is in the
trace. Treat the Langfuse data like the transcripts in `~/.claude/projects`: do not share
a trace, a screenshot of one or an export without reading it first.

Nothing leaves the machine: the ports listen on `127.0.0.1` only, and Langfuse's usage
telemetry is off.

## What you need

- A Docker engine with Compose, given **4 CPUs and 8 GiB of memory**. With
  [Colima](https://github.com/abiosoft/colima): `colima start --cpu 4 --memory 8`. The
  size is fixed when the VM is created; `colima stop` and start again to change it.
- About 6 GB of disk for the images, plus the traces.
- `uv` on `PATH`. The plugin's hook runs as a uv script.

## Install

In a normal terminal, not inside `claude-sb`:

```bash
make langfuse-install
```

It clones the pinned release to `~/opt/langfuse` (`LANGFUSE_HOME` changes the place),
writes `.env` there with generated passwords (mode 600, never printed), turns telemetry
off, pins the images, binds the ports to `127.0.0.1`, starts the seven containers and
checks them. Run it again at any time: it changes only what differs. On an install that
exists already it keeps the passwords and the traces, and asks before moving it to the
pinned release.

Then, once:

1. Open <http://localhost:3000>, sign up, create an organisation and a project, and under
   Settings, API Keys, a key pair. The account exists only on your machine.
2. Store both keys in the Keychain. `security` asks for the value, so it never lands in
   your shell history:

   ```bash
   security add-generic-password -U -a "$USER" -s langfuse-public-key -w
   security add-generic-password -U -a "$USER" -s langfuse-secret-key -w
   ```

3. Add these lines to `~/.zprofile` (`python3 tools/langfuse-local.py profile` prints
   them), then open a new terminal:

   ```bash
   # ~/.zprofile — only if not set yet, so a value passed in from outside wins
   [[ -z $LANGFUSE_PUBLIC_KEY ]] && LANGFUSE_PUBLIC_KEY=$(security find-generic-password -a "$USER" -s langfuse-public-key -w 2>/dev/null) && export LANGFUSE_PUBLIC_KEY
   [[ -z $LANGFUSE_SECRET_KEY ]] && LANGFUSE_SECRET_KEY=$(security find-generic-password -a "$USER" -s langfuse-secret-key -w 2>/dev/null) && export LANGFUSE_SECRET_KEY
   export LANGFUSE_BASE_URL=http://localhost:3000
   export CC_LANGFUSE_STATE_DIR="$HOME/.claude/cache/langfuse"
   ```

   On Linux, read the keys from your secret store the same way
   (`secret-tool lookup service langfuse-secret-key`).
4. Install the plugin, pinned, and restart Claude Code:

   ```bash
   make langfuse-plugin
   ```

Send one message in Claude Code and look for the trace at <http://localhost:3000>. When
none arrives, the hook says why in `~/.claude/cache/langfuse/langfuse_hook.log`.

## Everyday

```bash
make langfuse-status   # seven containers up, ports local only, the pinned version
make langfuse-down     # stop; the traces stay
make langfuse-up       # start again
make doctor            # also says when the install is behind the pin
```

The containers restart with the Docker engine. With Colima that means after
`colima start`; Colima itself does not start at login unless you set that up.

`make langfuse-reset` deletes every trace, the account, the API keys and the passwords.
It lists what goes and asks first.

## Why the keys are exported from the shell

The plugin offers to keep the secret key itself (`/plugin configure`), in the Keychain.
`claude-sb` closes the Keychain, so there the hook finds no key and switches tracing off
without a message. A variable exported in the shell reaches both `claude` and
`claude-sb`, and the hook reads it before the plugin's own setting. Set all three
(`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`) in the shell and none
in `/plugin configure`: the hook warns about a mix, and a key sent to the wrong host is
refused.

The "only if not set yet" check matters inside `claude-sb`: a shell started there reads
`~/.zprofile` again, the Keychain read fails, and without the check the key would be
emptied.

Two consequences of plain variables:

- **A project that sets its own `LANGFUSE_*` variables wins.** With direnv or an exported
  `.env` pointing at another Langfuse, your Claude Code transcript of that project goes
  there, not to your machine.
- **Everything started from that shell can read the key**, an agent in `claude-sb`
  included. The key opens only the Langfuse on your machine, which holds the traces of
  all your sessions.

## In claude-sb

| Profile | Traced | Why |
| --- | --- | --- |
| supervised (the default) | yes | The network is open, so `localhost:3000` and PyPI are reachable, and `~/.cache` and `~/.claude/cache` are writable. |
| strict | no | It refuses loopback addresses, and a personal policy can add entries but not remove that one. PyPI and uv's cache are closed too unless you open them. |

`CC_LANGFUSE_STATE_DIR` is needed for the supervised profile: the hook keeps its state,
lock and log in `~/.claude/state` by default, which the sandbox does not let it write.
`~/.claude/cache` is writable in both profiles, and one folder for `claude` and
`claude-sb` keeps one record of what was already sent.

Install and update the plugin in plain `claude`: `~/.claude/plugins` is closed for
writing in the sandbox.

## Updating

The versions are pinned in `upstream.json` (`langfuse.server`, `langfuse.plugin`), each
with the commit its tag pointed at. After a pull that moves a pin, `make update` and
`make doctor` say so, and `make langfuse-install` and `make langfuse-plugin` apply it.
Langfuse migrates its databases when a newer version starts; that cannot be undone, so
there is no way back to an older pin short of `make langfuse-reset`.

How the pins are chosen and what the plugin can reach: `UPSTREAM.md`, *Langfuse, run
locally*.
