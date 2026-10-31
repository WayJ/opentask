"""Update command - Check and install latest CLI version."""
import sys
import os
import re
import click
import subprocess
import urllib.request
import urllib.error
from typing import Optional, Tuple

# Get VERSION from package init
from opentask import __version__ as VERSION
from ..utils.repl_skin import ReplSkin


class Context:
    """CLI context object - minimal version for update command."""
    
    def __init__(self, json_mode: bool = False):
        self.json_mode = json_mode


# Default marketplace URL where version info is hosted
DEFAULT_MARKETPLACE_URL = os.environ.get("OPENTASK_MARKETPLACE_URL", "")
VERSION_FILE = "opentask-version.txt"


class UpdateError(Exception):
    """Update error."""
    pass


def get_current_version() -> str:
    """Get current installed version."""
    return VERSION


def fetch_latest_version(marketplace_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Fetch latest version info from marketplace.
    
    Returns:
        Tuple of (version, build_time, download_url)
    """
    version_url = f"{marketplace_url}/{VERSION_FILE}"
    
    try:
        with urllib.request.urlopen(version_url, timeout=10) as response:
            content = response.read().decode('utf-8')
        
        version = None
        build_time = None
        commit = None
        
        for line in content.strip().split('\n'):
            if line.startswith('version='):
                version = line.split('=', 1)[1].strip()
            elif line.startswith('build_time='):
                build_time = line.split('=', 1)[1].strip()
            elif line.startswith('build_commit='):
                commit = line.split('=', 1)[1].strip()
        
        if version:
            return version, build_time, commit
        return None, None, None
        
    except Exception as e:
        raise UpdateError(f"Failed to fetch version info: {e}")


def compare_versions(current: str, latest: str) -> int:
    """Compare versions.
    
    Returns:
        -1 if current < latest
         0 if current == latest
         1 if current > latest
    """
    def parse_version(v: str) -> Tuple[int, ...]:
        # Remove 'v' prefix if present
        v = v.lstrip('v')
        # Extract numeric parts
        parts = re.findall(r'\d+', v)
        return tuple(int(p) for p in parts)
    
    current_parts = parse_version(current)
    latest_parts = parse_version(latest)
    
    if current_parts < latest_parts:
        return -1
    elif current_parts > latest_parts:
        return 1
    else:
        return 0


def get_package_url(marketplace_url: str) -> str:
    """Get the package download URL."""
    return f"{marketplace_url}/opentask_cli-latest-py3-none-any.whl"


def install_update(whl_url: str) -> bool:
    """Download and install the update using pip."""
    import tempfile
    import shutil
    
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        whl_path = os.path.join(temp_dir, "opentask_cli.whl")
        
        # Download the file
        click.echo(f"Downloading from {whl_url}...")
        urllib.request.urlretrieve(whl_url, whl_path)
        
        # Install using pip
        click.echo("Installing update...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--force-reinstall", whl_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            click.echo(f"Installation failed: {result.stderr}", err=True)
            return False
        
        return True
        
    except Exception as e:
        raise UpdateError(f"Failed to install update: {e}")
    finally:
        # Cleanup temp directory
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)


@click.group(name="update")
def update_cli():
    """Update management."""
    pass


@update_cli.command(name="check")
@click.option("--marketplace-url", "-m", default=DEFAULT_MARKETPLACE_URL, help="Marketplace URL")
@click.pass_obj
def update_check(obj: Context, marketplace_url: str):
    """Check for available updates."""
    skin: ReplSkin = obj.skin
    
    current_version = get_current_version()
    
    skin.section("Update Check")
    skin.status("Current Version", current_version)
    skin.hint(f"Checking {marketplace_url}...")
    
    try:
        latest_version, build_time, commit = fetch_latest_version(marketplace_url)
        
        if not latest_version:
            skin.error("Failed to fetch latest version info")
            return
        
        skin.status("Latest Version", latest_version)
        
        if build_time:
            skin.status("Build Time", build_time)
        if commit:
            skin.status("Build Commit", commit)
        
        # Compare versions
        comparison = compare_versions(current_version, latest_version)
        
        if comparison < 0:
            skin.warning(f"\n✨ A new version ({latest_version}) is available!")
            skin.hint(f"Run: opentask update install")
        elif comparison == 0:
            skin.success(f"\n✓ You are running the latest version")
        else:
            skin.hint(f"\nℹ You are running a newer version than released ({current_version} > {latest_version})")
            
    except UpdateError as e:
        skin.error(f"Update check failed: {e}")


@update_cli.command(name="install")
@click.option("--marketplace-url", "-m", default=DEFAULT_MARKETPLACE_URL, help="Marketplace URL")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_obj
def update_install(obj: Context, marketplace_url: str, yes: bool):
    """Install the latest version."""
    skin: ReplSkin = obj.skin
    
    current_version = get_current_version()
    
    skin.section("Installing Update")
    
    try:
        latest_version, build_time, commit = fetch_latest_version(marketplace_url)
        
        if not latest_version:
            skin.error("Failed to fetch latest version info")
            return
        
        # Check if update is needed
        comparison = compare_versions(current_version, latest_version)
        
        if comparison >= 0:
            if comparison == 0:
                skin.success("You are already running the latest version")
            else:
                skin.hint(f"You are running a newer version ({current_version}) than available ({latest_version})")
            return
        
        # Show update info
        skin.status("Current Version", current_version)
        skin.status("New Version", latest_version)
        
        if not yes:
            skin.hint("\nThis command will:")
            skin.hint("  1. Download the latest CLI package")
            skin.hint("  2. Reinstall the opentask package")
            skin.hint("  3. You may need to restart your terminal")
            
            if not click.confirm("\nProceed with update?"):
                skin.hint("Update cancelled")
                return
        
        # Perform installation
        whl_url = f"{marketplace_url}/opentask_cli-latest-py3-none-any.whl"
        
        success = install_update(whl_url)
        
        if success:
            skin.success(f"\n✓ Successfully updated to version {latest_version}")
            skin.hint("Please restart your terminal for changes to take effect")
            
            # Show how to verify
            skin.hint(f"\nTo verify, run: opentask update check")
        else:
            skin.error("Update failed")
            
    except UpdateError as e:
        skin.error(f"Update failed: {e}")


@update_cli.command(name="version")
@click.option("--marketplace-url", "-m", default=DEFAULT_MARKETPLACE_URL, help="Marketplace URL")
@click.pass_obj
def update_version(obj: Context, marketplace_url: str):
    """Show version information for current and latest."""
    skin: ReplSkin = obj.skin
    
    current_version = get_current_version()
    
    skin.section("Version Information")
    skin.status("Installed Version", current_version)
    skin.status("Marketplace URL", marketplace_url)
    
    try:
        latest_version, build_time, commit = fetch_latest_version(marketplace_url)
        
        if latest_version:
            skin.status("Latest Version", latest_version)
            if build_time:
                skin.status("Build Time", build_time)
            if commit:
                skin.status("Build Commit", commit)
                
            comparison = compare_versions(current_version, latest_version)
            if comparison < 0:
                status = "Update available"
                skin.warning(status)
            elif comparison == 0:
                status = "Up to date"
                skin.success(status)
            else:
                status = "Ahead of release"
                skin.hint(status)
        else:
            skin.error("Could not fetch latest version info")
            
    except UpdateError as e:
        skin.error(f"Failed to fetch version info: {e}")
