class Infinitecontex < Formula
  include Language::Python::Virtualenv

  desc "Local-first project memory engine for AI coding workflows"
  homepage "https://github.com/desenyon/infinitecontex"
  url "https://github.com/desenyon/infinitecontex/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SHA"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/infctx", "--version"
  end
end
