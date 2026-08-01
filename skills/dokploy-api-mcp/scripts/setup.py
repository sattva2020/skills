#!/usr/bin/env python3
"""
Dokploy API MCP Skill — Interactive Setup

Registers the @sattva/dokploy-mcp server with Claude Code and validates the
connection to your Dokploy instance.

Usage:
  python3 setup.py
  python3 setup.py --url https://dokploy.example.com --key YOUR_KEY
  python3 setup.py --url ... --key ... --mode gateway   # 4 tools instead of 540
  python3 setup.py --insecure ...                       # only for self-signed certs
"""

import json
import os
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

CLAUDE_JSON = os.path.expanduser("~/.claude.json")
MODES = ("tools", "gateway", "both")


def get_input(prompt, default=None):
    """Get user input with optional default."""
    prompt = f"{prompt} [{default}]: " if default else f"{prompt}: "
    value = input(prompt).strip()
    return value if value else default


def parse_args():
    """Parse --url, --key, --mode and --insecure from the command line."""
    args = sys.argv[1:]
    out = {"url": None, "key": None, "mode": None, "insecure": "--insecure" in args}
    flags = {"--url": "url", "--key": "key", "--mode": "mode"}
    i = 0
    while i < len(args):
        if args[i] in flags and i + 1 < len(args):
            out[flags[args[i]]] = args[i + 1]
            i += 2
        else:
            i += 1
    return out


def normalize_url(url):
    """
    Strip a trailing /api.

    The MCP server appends /api itself, so a base URL ending in /api produces
    requests to /api/api/... and every call fails.
    """
    url = url.strip().rstrip("/")
    if url.endswith("/api"):
        url = url[: -len("/api")]
    return url


# Set by --insecure. Off by default: this script sends your API key, and an
# unverified connection is exactly where it would leak.
INSECURE = False


def _request(url, key, timeout=10):
    req = urllib.request.Request(url, headers={"x-api-key": key})
    ctx = ssl.create_default_context()
    if INSECURE:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return json.loads(resp.read())


def validate_connection(url, key):
    """Test the connection by calling settings.health."""
    try:
        return True, _request(f"{url}/api/settings.health", key)
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except ssl.SSLCertVerificationError as e:
        return False, (
            f"TLS certificate verification failed ({e.verify_message or e}). "
            "If this instance uses a self-signed certificate, re-run with --insecure "
            "— but note that your API key would then travel over an unverified "
            "connection. Trusting the certificate properly is the safer fix."
        )
    except Exception as e:  # noqa: BLE001 — surface whatever went wrong
        return False, str(e)


def count_endpoints(url, key):
    """Ask the instance how many endpoints its spec exposes."""
    try:
        spec = _request(f"{url}/api/settings.getOpenApiDocument", key, timeout=20)
        paths = spec.get("paths") or {}
        methods = {"get", "post", "put", "delete", "patch"}
        return sum(len(methods & set(item)) for item in paths.values())
    except Exception:  # noqa: BLE001
        return None


def list_projects(url, key):
    """Fetch the project list to verify full API access."""
    try:
        data = _request(f"{url}/api/trpc/project.all", key)
        return data.get("result", {}).get("data", {}).get("json", []) or []
    except Exception:  # noqa: BLE001
        return []


def build_server_config(url, key, mode):
    """MCP server entry. npx works on every platform Claude Code supports."""
    env = {"DOKPLOY_URL": url, "DOKPLOY_API_KEY": key}
    if mode and mode != "tools":
        env["DOKPLOY_MODE"] = mode

    config = {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@sattva/dokploy-mcp@latest"],
        "env": env,
    }
    if os.name == "nt":
        # On Windows npx must be launched through cmd
        config["command"] = "cmd"
        config["args"] = ["/c", "npx", "-y", "@sattva/dokploy-mcp@latest"]
    return config


def register_with_cli(config):
    """
    Register through the Claude CLI — it owns ~/.claude.json and knows where
    the current version keeps MCP servers. Returns True on success.
    """
    claude = shutil.which("claude")
    if not claude:
        return False
    try:
        result = subprocess.run(
            [claude, "mcp", "add-json", "dokploy", json.dumps(config), "--scope", "user"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return True
        print(f"  claude mcp add-json failed: {(result.stderr or result.stdout).strip()[:200]}")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"  Could not run the Claude CLI: {e}")
        return False


def print_manual_instructions(config):
    """Fallback: show the exact JSON instead of editing ~/.claude.json blindly."""
    print("  Add this to the \"mcpServers\" object in your Claude config")
    print(f"  ({CLAUDE_JSON} for Claude Code):")
    print()
    for line in json.dumps({"dokploy": config}, indent=2).splitlines():
        print(f"    {line}")
    print()
    print("  The file also holds your other settings — edit it, do not overwrite it.")


def main():
    print("=" * 52)
    print("  Dokploy API MCP Skill — Setup")
    print("=" * 52)
    print()

    args = parse_args()

    global INSECURE
    INSECURE = args["insecure"]
    if INSECURE:
        print("  WARNING: --insecure — TLS certificates will not be verified.")
        print("  Your API key travels over an unverified connection.")
        print()

    # Step 1: Dokploy URL
    if args["url"]:
        dokploy_url = args["url"]
    else:
        print("Step 1/4: Dokploy URL")
        print("  Your Dokploy dashboard URL, e.g. https://dokploy.example.com")
        print("  Do NOT add /api — the MCP server appends it itself.")
        print()
        dokploy_url = get_input("  Dokploy URL")

    if not dokploy_url:
        print("\n  ERROR: URL is required.")
        sys.exit(1)

    raw_url = dokploy_url.strip().rstrip("/")
    dokploy_url = normalize_url(dokploy_url)
    if raw_url != dokploy_url:
        print(f"  Note: stripped the trailing /api — using {dokploy_url}")
    print()

    # Step 2: API key
    if args["key"]:
        api_key = args["key"]
    else:
        print("Step 2/4: API Key")
        print("  Generate at: Dashboard -> Settings -> Profile -> API/CLI -> Generate")
        print()
        api_key = get_input("  API Key")

    if not api_key:
        print("\n  ERROR: API key is required.")
        sys.exit(1)
    print()

    # Step 3: validate
    print("Step 3/4: Validating connection...")
    ok, result = validate_connection(dokploy_url, api_key)

    endpoint_count = None
    if not ok:
        print(f"\n  ERROR: cannot reach Dokploy: {result}")
        print(f"  URL tried: {dokploy_url}/api/settings.health")
        print()
        if (get_input("  Save the config anyway? (y/N)", "N") or "").lower() != "y":
            sys.exit(1)
    else:
        print("  OK — Dokploy is reachable")
        endpoint_count = count_endpoints(dokploy_url, api_key)
        if endpoint_count:
            print(f"  API exposes {endpoint_count} endpoints")
        projects = list_projects(dokploy_url, api_key)
        if projects:
            print(f"\n  Found {len(projects)} project(s):")
            for p in projects[:5]:
                print(f"    - {p.get('name', '?')}")
            if len(projects) > 5:
                print(f"    ... and {len(projects) - 5} more")
    print()

    # Step 4: surface mode
    mode = (args["mode"] or "").lower()
    if mode and mode not in MODES:
        print(f"  Unknown --mode {mode}, falling back to 'tools'")
        mode = ""
    if not mode:
        total = endpoint_count or 540
        print("Step 4/4: Tool surface")
        print(f"  tools   — one tool per endpoint (~{total}); familiar, but a large tool list")
        print("  gateway — 4 tools (search/describe/call/mutate) covering the whole API;")
        print("            ~99% less context, at the cost of a lookup before each call")
        print("  both    — both surfaces at once")
        print()
        mode = (get_input("  Mode (tools/gateway/both)", "tools") or "tools").lower()
        if mode not in MODES:
            mode = "tools"
    print()

    # Register
    config = build_server_config(dokploy_url, api_key, mode)
    if register_with_cli(config):
        print(f"  Registered the 'dokploy' MCP server (mode: {mode})")
    else:
        print("  Automatic registration unavailable — configure it manually:")
        print()
        print_manual_instructions(config)

    print()
    print("=" * 52)
    print("  Setup complete")
    print()
    print(f"  Dokploy: {dokploy_url}")
    print(f"  Mode:    {mode}")
    print()
    print("  Restart Claude Code to activate the server.")
    print("  Then use /dokploy-api-mcp to deploy your apps.")
    print("=" * 52)


if __name__ == "__main__":
    main()
