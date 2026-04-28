# Adding A Host

mStack keeps host-specific install details in `config/hosts.json`. The installer should not grow a new branch for every agent host.

## Host Entry Shape

```json
{
  "hosts": {
    "codex": {
      "displayName": "OpenAI Codex",
      "aliases": ["codex"],
      "homeEnv": "CODEX_HOME",
      "defaultHome": "~/.codex",
      "skillDir": "skills",
      "defaultPrefix": "mstack",
      "generatedRoot": ".agents/skills/mstack",
      "frontmatter": {
        "mode": "allowlist",
        "keepFields": ["name", "description"],
        "descriptionLimit": 1024,
        "descriptionLimitBehavior": "error"
      },
      "generation": {
        "generateMetadata": true,
        "metadataFormat": "openai.yaml"
      },
      "pathRewrites": []
    }
  }
}
```

Fields:

- `aliases`: command-line names accepted by `./setup --host`.
- `homeEnv`: environment variable that overrides the host home directory.
- `defaultHome`: fallback home directory when the env var is unset.
- `skillDir`: skill directory relative to the host home.
- `defaultPrefix`: expected skill prefix. Keep this as `mstack` unless the host has a hard technical reason not to.
- `generatedRoot`: ignored sidecar path for host-transformed skill docs.
- `frontmatter`: host-specific frontmatter allowlist and description limits.
- `generation`: whether to generate sidecar metadata such as `agents/openai.yaml`.
- `pathRewrites`: literal replacements applied to generated host docs.

## Add The Host

1. Add the entry to `config/hosts.json`.
2. Run:

```bash
bin/mstack-check
```

3. Generate host docs:

```bash
scripts/host_config.py generate --host new-host
```

4. Test direct install:

```bash
HOST_HOME="$(mktemp -d)" ./setup --host new-host --force
```

If the new host uses a different env var, replace `HOST_HOME` with the `homeEnv` value from `config/hosts.json`.

5. Test `--host all`:

```bash
./setup --host all --force
```

6. Update `README.md`, `CONTRIBUTING.md`, and any host-specific project guidance.

## Host Contract

A host should be able to consume each installed skill directory as:

```text
skill-name/
|-- SKILL.md
`-- agents/
    `-- openai.yaml
```

The generated `SKILL.md` must have a `name:` field that matches the runtime command. For example, a prefixed install should write:

```yaml
name: mstack-product-context
```

This is why `setup` creates runtime skill directories instead of symlinking a prefixed directory directly to the source skill directory.

## If A Host Needs A Different Layout

Keep the generic host metadata in `config/hosts.json`, then add a small installer function for the unusual layout. Do not change the source skill directories to match one host's quirks.
