#!/bin/bash
# Quick packaging and distribution testing script

set -e

VERSION=$(python3 - <<'PY'
from pathlib import Path

pyproject = Path("pyproject.toml")
if pyproject.exists():
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("version"):
            print(line.split("=", 1)[1].strip().strip('"'))
            raise SystemExit

version = Path("VERSION")
print(version.read_text(encoding="utf-8").strip() if version.exists() else "0.0.0")
PY
)
PROJECT_NAME="beacon-readiness"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Beacon Package Builder v${VERSION}${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"

# Parse arguments
BUILD_TYPE="${1:-all}"

show_help() {
    cat << EOF
Usage: ./scripts/package.sh [COMMAND]

Commands:
    all         Build everything (default)
    check       Check build requirements
    wheel       Build Python wheel only
    source      Build Python source distribution
    binary      Build standalone binary for current platform
    macos-pkg   Build macOS .pkg installer
    test-wheel  Test the built wheel locally
    test-pypi   Test upload to TestPyPI
    clean       Clean build artifacts

Examples:
    ./scripts/package.sh check
    ./scripts/package.sh wheel
    ./scripts/package.sh binary
    ./scripts/package.sh macos-pkg
    ./scripts/package.sh test-wheel
EOF
}

check_requirements() {
    echo -e "\n${YELLOW}→ Checking requirements...${NC}"

    local missing=0

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python 3 not found${NC}"
        missing=1
    else
        echo -e "${GREEN}✓ Python 3: $(python3 --version)${NC}"
    fi

    # Check pip
    if ! python3 -m pip --version &> /dev/null; then
        echo -e "${RED}✗ pip not found${NC}"
        missing=1
    else
        echo -e "${GREEN}✓ pip available${NC}"
    fi

    # Check required packages
    for pkg in build twine; do
        if python3 -m pip show $pkg > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $pkg installed${NC}"
        else
            echo -e "${YELLOW}⚠ $pkg not installed (will install)${NC}"
        fi
    done

    if [ $missing -eq 1 ]; then
        echo -e "${RED}✗ Missing required tools${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ All requirements met${NC}"
    return 0
}

install_build_tools() {
    echo -e "\n${YELLOW}→ Installing build tools...${NC}"
    pip3 install --upgrade build twine wheel
    echo -e "${GREEN}✓ Build tools installed${NC}"
}

build_wheel() {
    echo -e "\n${YELLOW}→ Building wheel...${NC}"

    if [ ! -f "pyproject.toml" ]; then
        echo -e "${RED}✗ pyproject.toml not found${NC}"
        return 1
    fi

    # Clean previous builds
    rm -rf build dist *.egg-info

    # Build
    python3 -m build --wheel

    if [ -f "dist/${PROJECT_NAME}-${VERSION}-py3-none-any.whl" ]; then
        echo -e "${GREEN}✓ Wheel built: dist/${PROJECT_NAME}-${VERSION}-py3-none-any.whl${NC}"
        ls -lh dist/*.whl
        return 0
    else
        echo -e "${RED}✗ Wheel build failed${NC}"
        return 1
    fi
}

build_source() {
    echo -e "\n${YELLOW}→ Building source distribution...${NC}"

    python3 -m build --sdist

    if [ -f "dist/${PROJECT_NAME}-${VERSION}.tar.gz" ]; then
        echo -e "${GREEN}✓ Source distribution built: dist/${PROJECT_NAME}-${VERSION}.tar.gz${NC}"
        ls -lh dist/*.tar.gz
        return 0
    else
        echo -e "${RED}✗ Source distribution build failed${NC}"
        return 1
    fi
}

build_binary() {
    echo -e "\n${YELLOW}→ Building standalone binary...${NC}"

    if ! python3 -m pip show pyinstaller > /dev/null 2>&1; then
        echo -e "${YELLOW}  Installing PyInstaller...${NC}"
        pip3 install pyinstaller
    fi

    python3 scripts/build_binaries.py
    return 0
}

build_macos_pkg() {
    echo -e "\n${YELLOW}→ Building macOS .pkg installer...${NC}"

    if [ "$(uname -s)" != "Darwin" ]; then
        echo -e "${RED}✗ macOS .pkg installers must be built on macOS${NC}"
        return 1
    fi

    if ! command -v pkgbuild > /dev/null 2>&1 || ! command -v productbuild > /dev/null 2>&1; then
        echo -e "${RED}✗ pkgbuild and productbuild are required. Install Xcode Command Line Tools.${NC}"
        return 1
    fi

    python3 scripts/build_macos_pkg.py
    return 0
}

check_distribution() {
    echo -e "\n${YELLOW}→ Checking distributions...${NC}"

    python3 -m twine check dist/* || true

    echo -e "\n${GREEN}✓ Distribution check complete${NC}"
}

test_wheel() {
    echo -e "\n${YELLOW}→ Testing wheel installation...${NC}"

    if [ ! -f "dist/${PROJECT_NAME}-${VERSION}-py3-none-any.whl" ]; then
        echo -e "${RED}✗ Wheel not found. Build it first: ./scripts/package.sh wheel${NC}"
        return 1
    fi

    # Create test venv
    TEST_VENV=$(mktemp -d)
    echo -e "  Using test venv: ${TEST_VENV}"

    python3 -m venv "${TEST_VENV}"
    source "${TEST_VENV}/bin/activate"

    # Install requirements
    pip3 install --upgrade pip
    pip3 install -r requirements.txt

    # Install wheel
    pip3 install "dist/${PROJECT_NAME}-${VERSION}-py3-none-any.whl"

    # Test command
    echo -e "\n${YELLOW}  Testing: beacon --help${NC}"
    beacon --help > /dev/null

    echo -e "\n${YELLOW}  Testing: beacon --version${NC}"
    beacon --version 2>/dev/null || beacon readiness --help > /dev/null

    # Cleanup
    deactivate
    rm -rf "${TEST_VENV}"

    echo -e "${GREEN}✓ Wheel test passed${NC}"
    return 0
}

test_pypi() {
    echo -e "\n${YELLOW}→ Preparing TestPyPI upload...${NC}"
    echo -e "  Note: Requires TestPyPI token in ~/.pypirc"
    echo -e "\n${YELLOW}  To upload to TestPyPI:${NC}"
    echo -e "    twine upload --repository testpypi dist/*"
    echo -e "\n${YELLOW}  To install from TestPyPI:${NC}"
    echo -e "    pip install --index-url https://test.pypi.org/simple/ beacon-readiness"
}

clean() {
    echo -e "\n${YELLOW}→ Cleaning build artifacts...${NC}"

    rm -rf build dist dist-binaries *.egg-info
    rm -rf **/__pycache__ **/*.pyc
    rm -rf .pytest_cache .coverage htmlcov

    echo -e "${GREEN}✓ Clean complete${NC}"
}

# Main
case "$BUILD_TYPE" in
    all)
        check_requirements || install_build_tools
        build_wheel
        build_source
        check_distribution
        ;;
    check)
        check_requirements
        ;;
    wheel)
        check_requirements || install_build_tools
        build_wheel
        ;;
    source)
        check_requirements || install_build_tools
        build_source
        ;;
    binary)
        build_binary
        ;;
    macos-pkg)
        build_macos_pkg
        ;;
    test-wheel)
        test_wheel
        ;;
    test-pypi)
        test_pypi
        ;;
    clean)
        clean
        ;;
    help)
        show_help
        ;;
    *)
        echo -e "${RED}✗ Unknown command: $BUILD_TYPE${NC}"
        show_help
        exit 1
        ;;
esac
