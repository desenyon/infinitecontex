class Infinitecontex < Formula
  include Language::Python::Virtualenv

  desc "Local-first project memory engine for AI coding workflows"
  homepage "https://github.com/desenyon/infinitecontex"
  url "https://github.com/desenyon/infinitecontex/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "72c4a16a92862c9ecd7936e6ec02888b9c6799092e7d9b427bf008cf37705447"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/infctx", "--version"
  end
end
