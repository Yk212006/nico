#!/usr/bin/env bash
# ──────────────────────────────────────────────
# Build NICO .deb package for Raspberry Pi
# ──────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
PACKAGE_NAME="nico"
VERSION="0.2.0"
ARCH="arm64"
DEB_DIR="$BUILD_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "=== Building NICO .deb package ==="
echo ""

# Clean
rm -rf "$BUILD_DIR"
mkdir -p "$DEB_DIR"

# ── 1. Copy project source to /opt/nico/ ─────
echo "[1/4] Copying source files..."
mkdir -p "$DEB_DIR/opt/nico"

# Core application
cp -r "$PROJECT_DIR/nico" "$DEB_DIR/opt/nico/nico"
cp -r "$PROJECT_DIR/friday" "$DEB_DIR/opt/nico/friday"
cp "$PROJECT_DIR/main.py" "$DEB_DIR/opt/nico/"
cp "$PROJECT_DIR/server.py" "$DEB_DIR/opt/nico/"
cp "$PROJECT_DIR/pyproject.toml" "$DEB_DIR/opt/nico/"
cp "$PROJECT_DIR/setup_assistant.py" "$DEB_DIR/opt/nico/"
cp "$PROJECT_DIR/get_assistant_token.py" "$DEB_DIR/opt/nico/"
cp "$PROJECT_DIR/.env.example" "$DEB_DIR/opt/nico/"
cp "$PROJECT_DIR/profiles" "$DEB_DIR/opt/nico/" -r
cp "$PROJECT_DIR/README_NICO.md" "$DEB_DIR/opt/nico/"

# Install script for post-setup
cp "$PROJECT_DIR/install.sh" "$DEB_DIR/opt/nico/"

# Create empty nico_files dir
mkdir -p "$DEB_DIR/opt/nico/nico_files"

echo ""

# ── 2. Create systemd service ────────────────
echo "[2/4] Creating systemd service..."
mkdir -p "$DEB_DIR/etc/systemd/system"
cp "$SCRIPT_DIR/debian/nico.service" "$DEB_DIR/etc/systemd/system/nico.service"

# ── 3. Create DEBIAN control files ───────────
echo "[3/4] Creating DEBIAN control files..."
mkdir -p "$DEB_DIR/DEBIAN"

# control
cp "$SCRIPT_DIR/debian/control" "$DEB_DIR/DEBIAN/control"

# postinst
cp "$SCRIPT_DIR/debian/postinst" "$DEB_DIR/DEBIAN/postinst"
chmod 755 "$DEB_DIR/DEBIAN/postinst"

# prerm
cp "$SCRIPT_DIR/debian/prerm" "$DEB_DIR/DEBIAN/prerm"
chmod 755 "$DEB_DIR/DEBIAN/prerm"

# conffiles
echo "/etc/nico/.env" > "$DEB_DIR/DEBIAN/conffiles"

echo ""

# ── 4. Build the .deb ────────────────────────
echo "[4/4] Building .deb package..."
fakeroot dpkg-deb --build "$DEB_DIR"

OUTPUT_DEB="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
mv "${DEB_DIR}.deb" "$OUTPUT_DEB"

echo ""
echo "=== Done! ==="
echo "Package: $OUTPUT_DEB"
echo "Size: $(du -h "$OUTPUT_DEB" | cut -f1)"
echo ""
echo "Install on Raspberry Pi:"
echo "  sudo dpkg -i $OUTPUT_DEB"
echo "  sudo apt install -f   # fix any missing deps"
echo ""
